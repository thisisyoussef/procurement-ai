"""Buyer context assembly and cross-project user profile learning helpers."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.core.database import async_session_factory
from app.repositories.user_repository import get_user_by_id
from app.schemas.agent_state import ParsedRequirements
from app.schemas.buyer_context import BuyerContext
from app.schemas.user_profile import (
    CategoryExperience,
    SupplierRelationship,
    UserSourcingProfile,
)

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _set_field_path(context: BuyerContext, field_path: str, value: Any) -> bool:
    """Set a dotted field path on BuyerContext, returning True when applied."""
    if not field_path:
        return False

    parts = field_path.split(".")
    target: Any = context
    for part in parts[:-1]:
        if not hasattr(target, part):
            return False
        target = getattr(target, part)

    final = parts[-1]
    if not hasattr(target, final):
        return False

    setattr(target, final, value)
    return True


def _ensure_list_unique(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def _find_or_create_category(profile: UserSourcingProfile, category: str) -> CategoryExperience:
    key = category.strip().lower()
    for existing in profile.category_experience:
        if existing.category.strip().lower() == key:
            return existing
    created = CategoryExperience(category=category.strip() or "unknown")
    profile.category_experience.append(created)
    return created


def _update_supplier_relationship(
    profile: UserSourcingProfile,
    supplier_id: str,
    supplier_name: str,
    *,
    sentiment: str = "neutral",
    communication_rating: str | None = None,
) -> None:
    key = supplier_id or supplier_name
    if not key:
        return

    relationship: SupplierRelationship | None = None
    for existing in profile.supplier_relationships:
        if existing.supplier_id == supplier_id or existing.supplier_name.lower() == supplier_name.lower():
            relationship = existing
            break

    if relationship is None:
        relationship = SupplierRelationship(
            supplier_id=supplier_id or supplier_name,
            supplier_name=supplier_name,
            sentiment=sentiment,
            projects_together=0,
        )
        profile.supplier_relationships.append(relationship)

    relationship.projects_together += 1
    relationship.sentiment = sentiment or relationship.sentiment
    relationship.communication_rating = communication_rating or relationship.communication_rating
    relationship.last_interaction_date = datetime.now(timezone.utc).date()


async def _load_user_defaults(user_id: str) -> tuple[dict[str, Any], UserSourcingProfile]:
    async with async_session_factory() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            return {}, UserSourcingProfile()

        raw_profile = user.sourcing_profile or {}
        try:
            profile = UserSourcingProfile(**raw_profile)
        except Exception:
            logger.warning("User sourcing profile invalid for user %s; resetting", user_id, exc_info=True)
            profile = UserSourcingProfile()

        business_defaults = {
            "company_name": user.company_name,
            "business_address": user.business_address,
            "phone": user.phone,
            "default_buyer_context": user.default_buyer_context or {},
        }
        return business_defaults, profile


async def build_initial_buyer_context(
    user_id: str,
    parsed_requirements: ParsedRequirements,
) -> BuyerContext:
    """Build the initial BuyerContext from user profile, business profile, and parsed requirements."""
    business_defaults, profile = await _load_user_defaults(user_id)

    context = BuyerContext()

    # 1) Apply defaults from user's persisted buyer context snapshot.
    try:
        default_snapshot = business_defaults.get("default_buyer_context") or {}
        if isinstance(default_snapshot, dict) and default_snapshot:
            context = BuyerContext(**default_snapshot)
            context.inferred_fields.extend(
                [
                    "default_buyer_context",
                ]
            )
    except Exception:
        logger.warning("Invalid default buyer context for user %s", user_id, exc_info=True)

    # 2) Overlay business profile.
    business_address = business_defaults.get("business_address")
    if business_address and not context.logistics.shipping_address:
        context.logistics.shipping_address = business_address
        context.inferred_fields.append("logistics.shipping_address")

    # 3) Overlay sourcing profile preferences.
    if profile.default_shipping_address and not context.logistics.shipping_address:
        context.logistics.shipping_address = profile.default_shipping_address
        context.inferred_fields.append("logistics.shipping_address")
    if profile.default_port_of_entry and not context.logistics.port_of_entry:
        context.logistics.port_of_entry = profile.default_port_of_entry
        context.inferred_fields.append("logistics.port_of_entry")
    if profile.default_payment_methods and not context.financial.payment_methods:
        context.financial.payment_methods = list(profile.default_payment_methods)
        context.inferred_fields.append("financial.payment_methods")
    if profile.default_incoterms and not context.logistics.preferred_incoterms:
        context.logistics.preferred_incoterms = profile.default_incoterms
        context.inferred_fields.append("logistics.preferred_incoterms")
    if profile.default_quality_tier and not context.quality.quality_tier:
        context.quality.quality_tier = profile.default_quality_tier
        context.inferred_fields.append("quality.quality_tier")

    # 4) Overlay current request requirements.
    if parsed_requirements.delivery_location:
        context.logistics.shipping_city = parsed_requirements.delivery_location
        context.explicitly_provided_fields.append("logistics.shipping_city")
    if parsed_requirements.deadline:
        context.timeline.hard_deadline = parsed_requirements.deadline
        context.explicitly_provided_fields.append("timeline.hard_deadline")
    if parsed_requirements.priority_tradeoff:
        context.priority_tradeoff = parsed_requirements.priority_tradeoff
        context.explicitly_provided_fields.append("priority_tradeoff")
    if parsed_requirements.budget_range and not context.financial.budget_hard_cap:
        inferred_budget = _safe_float(parsed_requirements.budget_range.replace("$", "").split("-")[-1])
        if inferred_budget is not None:
            context.financial.budget_hard_cap = inferred_budget
            context.inferred_fields.append("financial.budget_hard_cap")

    if profile.import_experience_level in {"unknown", "first_time"}:
        context.is_first_import = True
    elif profile.import_experience_level in {"occasional", "regular"}:
        context.is_first_import = False

    context.sourced_this_category_before = False
    category = (parsed_requirements.product_type or "").strip().lower()
    if category:
        for entry in profile.category_experience:
            if entry.category.strip().lower() == category and entry.projects_completed > 0:
                context.sourced_this_category_before = True
                context.category_experience_level = "experienced"
                break

    context.explicitly_provided_fields = _ensure_list_unique(context.explicitly_provided_fields)
    context.inferred_fields = _ensure_list_unique(context.inferred_fields)
    return context


async def merge_checkpoint_answers(
    context: BuyerContext,
    checkpoint_answers: dict,
) -> BuyerContext:
    """Merge user answers from checkpoint interactions into BuyerContext."""
    if not checkpoint_answers:
        return context

    for field, value in checkpoint_answers.items():
        if value in (None, ""):
            continue
        applied = _set_field_path(context, field, value)
        if applied:
            context.explicitly_provided_fields.append(field)
        else:
            # Keep support for top-level convenience keys.
            if hasattr(context, field):
                setattr(context, field, value)
                context.explicitly_provided_fields.append(field)

    context.explicitly_provided_fields = _ensure_list_unique(context.explicitly_provided_fields)
    return context


async def update_user_profile_from_project(
    user_id: str,
    project_state: dict,
    buyer_context: BuyerContext,
    user_feedback: dict | None = None,
) -> None:
    """Update persistent UserSourcingProfile and default BuyerContext after a project."""
    async with async_session_factory() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            return

        try:
            profile = UserSourcingProfile(**(user.sourcing_profile or {}))
        except Exception:
            profile = UserSourcingProfile()

        parsed = project_state.get("parsed_requirements") or {}
        product_type = str(parsed.get("product_type") or "").strip() or "unknown"
        category = _find_or_create_category(profile, product_type)
        category.projects_completed += 1

        regions = []
        for supplier in (project_state.get("discovery_results") or {}).get("suppliers", []):
            country = str((supplier or {}).get("country") or "").strip()
            if country:
                regions.append(country)

        category.preferred_regions = _ensure_list_unique(category.preferred_regions + regions)
        profile.preferred_sourcing_regions = _ensure_list_unique(profile.preferred_sourcing_regions + regions)

        budget = buyer_context.financial.budget_hard_cap
        if budget is not None:
            prior = profile.average_project_budget
            if prior is None:
                profile.average_project_budget = float(budget)
            else:
                profile.average_project_budget = round((prior * max(profile.total_projects, 1) + float(budget)) / (profile.total_projects + 1), 2)

        profile.total_projects += 1
        profile.last_project_date = date.today()
        profile.default_shipping_address = buyer_context.logistics.shipping_address or profile.default_shipping_address
        profile.default_port_of_entry = buyer_context.logistics.port_of_entry or profile.default_port_of_entry
        profile.default_payment_methods = _ensure_list_unique(
            profile.default_payment_methods + (buyer_context.financial.payment_methods or [])
        )
        profile.default_incoterms = buyer_context.logistics.preferred_incoterms or profile.default_incoterms
        profile.default_quality_tier = buyer_context.quality.quality_tier or profile.default_quality_tier

        if profile.total_projects >= 5:
            profile.import_experience_level = "regular"
        elif profile.total_projects >= 2:
            profile.import_experience_level = "occasional"
        elif profile.total_projects == 1:
            profile.import_experience_level = "first_time"

        # Relationship updates from outreach state.
        outreach = project_state.get("outreach_state") or {}
        for status in outreach.get("supplier_statuses") or []:
            if not isinstance(status, dict):
                continue
            if not status.get("response_received"):
                continue
            supplier_name = str(status.get("supplier_name") or "").strip()
            supplier_id = str(status.get("supplier_id") or supplier_name)
            if supplier_name:
                _update_supplier_relationship(
                    profile,
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    sentiment="neutral",
                )

        # Apply retrospective feedback.
        if user_feedback:
            chosen = str(user_feedback.get("supplier_chosen") or "").strip()
            if chosen:
                _update_supplier_relationship(
                    profile,
                    supplier_id=chosen,
                    supplier_name=chosen,
                    sentiment="positive" if user_feedback.get("would_use_again") else "neutral",
                    communication_rating=(
                        "excellent" if (user_feedback.get("communication_rating") or 0) >= 4
                        else "poor" if (user_feedback.get("communication_rating") or 0) <= 2
                        else "good"
                    ) if user_feedback.get("communication_rating") is not None else None,
                )

        # Track common categories
        freq: dict[str, int] = {}
        for item in profile.category_experience:
            freq[item.category] = item.projects_completed
        profile.most_common_categories = [
            item[0] for item in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Persist profile and latest context snapshot.
        user.sourcing_profile = profile.model_dump(mode="json")
        user.default_buyer_context = buyer_context.model_dump(mode="json")
        await session.commit()
