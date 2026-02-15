"""Checkpoint event builders and steering application helpers."""

from __future__ import annotations

from typing import Any

from app.schemas.agent_state import (
    CheckpointEvent,
    CheckpointResponse,
    CheckpointType,
    ContextQuestion,
)
from app.schemas.buyer_context import BuyerContext


def _safe_len(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _questions_for(checkpoint_type: CheckpointType) -> list[ContextQuestion]:
    if checkpoint_type == CheckpointType.CONFIRM_REQUIREMENTS:
        return [
            ContextQuestion(
                field="logistics.has_customs_broker",
                question="Do you have a customs broker?",
                context="This changes which suppliers and incoterms are viable.",
                options=["Yes", "No", "Not sure"],
                default="Not sure",
            ),
            ContextQuestion(
                field="is_first_import",
                question="Is this your first import project?",
                context="First-time importers benefit from lower-risk suppliers and simpler terms.",
                options=["Yes", "No"],
                default="No",
            ),
        ]
    if checkpoint_type == CheckpointType.REVIEW_SUPPLIERS:
        return [
            ContextQuestion(
                field="quality.quality_tier",
                question="What quality tier are you targeting?",
                context="This affects who advances to deep verification.",
                options=["premium", "standard", "budget"],
                default="standard",
            ),
            ContextQuestion(
                field="quality.needs_samples_first",
                question="Do you want samples before committing?",
                context="Sample-first flows prioritize suppliers with stronger pre-production support.",
                options=["Yes", "No"],
                default="Yes",
            ),
        ]
    if checkpoint_type == CheckpointType.SET_CONFIDENCE_GATE:
        return [
            ContextQuestion(
                field="financial.budget_hard_cap",
                question="What is your total budget hard cap?",
                context="Budget cap helps trim risky candidates before comparison.",
            ),
            ContextQuestion(
                field="financial.payment_methods",
                question="Which payment methods can you use?",
                context="Payment flexibility influences supplier viability.",
                options=["wire", "credit_card", "lc", "trade_assurance"],
            ),
        ]
    if checkpoint_type == CheckpointType.ADJUST_WEIGHTS:
        return [
            ContextQuestion(
                field="priority_tradeoff",
                question="Should we prioritize cost, speed, or quality?",
                context="The recommendation ranking weights are adjusted based on this preference.",
                options=["lowest_cost", "fastest_delivery", "highest_quality", "balanced"],
                default="balanced",
            ),
        ]
    if checkpoint_type == CheckpointType.OUTREACH_PREFERENCES:
        return [
            ContextQuestion(
                field="quality.needs_samples_first",
                question="Should outreach request samples in the first email?",
                context="Sample requests change supplier response quality and timing.",
                options=["Yes", "No"],
                default="Yes",
            ),
            ContextQuestion(
                field="financial.payment_terms_preference",
                question="Do you want preferred payment terms mentioned?",
                context="This sets negotiation context before quotes arrive.",
            ),
        ]
    return []


def _event_for_requirements(state: dict[str, Any]) -> CheckpointEvent:
    parsed = state.get("parsed_requirements") or {}
    regions = [r.get("region") for r in (parsed.get("regional_searches") or []) if isinstance(r, dict)]
    return CheckpointEvent(
        checkpoint_type=CheckpointType.CONFIRM_REQUIREMENTS,
        summary=(
            f"Parsed request for {parsed.get('product_type') or 'product'}"
            f" with {len(parsed.get('search_queries') or [])} search queries."
        ),
        next_stage_preview="Next: multi-source supplier discovery.",
        context_questions=_questions_for(CheckpointType.CONFIRM_REQUIREMENTS),
        adjustable_parameters={
            "product_type": parsed.get("product_type"),
            "search_queries": parsed.get("search_queries") or [],
            "regional_searches": regions,
            "certifications_needed": parsed.get("certifications_needed") or [],
        },
        auto_continue_seconds=30,
    )


def _event_for_discovery(state: dict[str, Any]) -> CheckpointEvent:
    discovery = state.get("discovery_results") or {}
    suppliers = discovery.get("suppliers") or []
    return CheckpointEvent(
        checkpoint_type=CheckpointType.REVIEW_SUPPLIERS,
        summary=f"Found {len(suppliers)} suppliers across discovery sources.",
        next_stage_preview="Next: legitimacy and risk verification checks.",
        context_questions=_questions_for(CheckpointType.REVIEW_SUPPLIERS),
        adjustable_parameters={
            "minimum_supplier_count": (state.get("parsed_requirements") or {}).get("minimum_supplier_count"),
            "pin_suppliers": [],
            "remove_suppliers": [],
        },
        auto_continue_seconds=45,
    )


def _event_for_verification(state: dict[str, Any]) -> CheckpointEvent:
    verification = state.get("verification_results") or {}
    rows = verification.get("verifications") or []
    low = sum(1 for row in rows if (row.get("risk_level") == "low"))
    medium = sum(1 for row in rows if (row.get("risk_level") == "medium"))
    high = sum(1 for row in rows if (row.get("risk_level") == "high"))
    return CheckpointEvent(
        checkpoint_type=CheckpointType.SET_CONFIDENCE_GATE,
        summary=f"Verification complete: {low} low risk, {medium} medium risk, {high} high risk.",
        next_stage_preview="Next: side-by-side supplier comparison.",
        context_questions=_questions_for(CheckpointType.SET_CONFIDENCE_GATE),
        adjustable_parameters={
            "confidence_gate_threshold": state.get("confidence_gate_threshold", 30),
            "include_high_risk_suppliers": False,
        },
        auto_continue_seconds=30,
    )


def _event_for_comparison(state: dict[str, Any]) -> CheckpointEvent:
    comparison = state.get("comparison_result") or {}
    rows = comparison.get("comparisons") or []
    return CheckpointEvent(
        checkpoint_type=CheckpointType.ADJUST_WEIGHTS,
        summary=f"Compared {len(rows)} suppliers on cost, quality, risk, and lead time.",
        next_stage_preview="Next: recommendation synthesis and lane assignment.",
        context_questions=_questions_for(CheckpointType.ADJUST_WEIGHTS),
        adjustable_parameters={
            "weights": {
                "cost": 0.3,
                "quality": 0.3,
                "speed": 0.2,
                "risk": 0.2,
            }
        },
        auto_continue_seconds=30,
    )


def _event_for_recommendation(state: dict[str, Any]) -> CheckpointEvent:
    recommendation = state.get("recommendation_result") or {}
    rows = recommendation.get("recommendations") or []
    return CheckpointEvent(
        checkpoint_type=CheckpointType.OUTREACH_PREFERENCES,
        summary=f"Prepared {len(rows)} recommendations across decision lanes.",
        next_stage_preview="Next: outreach drafting for approved suppliers.",
        context_questions=_questions_for(CheckpointType.OUTREACH_PREFERENCES),
        adjustable_parameters={
            "suppliers_to_contact": [
                row.get("supplier_index")
                for row in rows[:5]
                if isinstance(row, dict)
            ],
            "email_tone": "professional",
        },
        auto_continue_seconds=30,
        requires_explicit_approval=True,
    )


def build_checkpoint_event(checkpoint_type: CheckpointType, state: dict[str, Any]) -> CheckpointEvent:
    """Build a checkpoint payload from current state."""
    if checkpoint_type == CheckpointType.CONFIRM_REQUIREMENTS:
        return _event_for_requirements(state)
    if checkpoint_type == CheckpointType.REVIEW_SUPPLIERS:
        return _event_for_discovery(state)
    if checkpoint_type == CheckpointType.SET_CONFIDENCE_GATE:
        return _event_for_verification(state)
    if checkpoint_type == CheckpointType.ADJUST_WEIGHTS:
        return _event_for_comparison(state)
    return _event_for_recommendation(state)


def _set_context_field(context: BuyerContext, field: str, value: Any) -> bool:
    if not field:
        return False

    parts = field.split(".")
    target: Any = context
    for part in parts[:-1]:
        if not hasattr(target, part):
            return False
        target = getattr(target, part)

    leaf = parts[-1]
    if not hasattr(target, leaf):
        return False

    setattr(target, leaf, value)
    return True


def apply_checkpoint_steering(
    state: dict[str, Any],
    response_payload: dict[str, Any],
    checkpoint_type: CheckpointType,
) -> dict[str, Any]:
    """Apply steering answers/overrides into graph state."""
    response = CheckpointResponse(**response_payload)

    # Merge answers into buyer context
    context = BuyerContext(**(state.get("buyer_context") or {}))
    for field, value in (response.answers or {}).items():
        if value in (None, ""):
            continue
        if _set_context_field(context, field, value):
            context.explicitly_provided_fields.append(field)

    next_state = dict(state)
    next_state["buyer_context"] = context.model_dump(mode="json")

    # Apply parameter overrides
    overrides = response.parameter_overrides or {}
    if "confidence_gate_threshold" in overrides:
        try:
            next_state["confidence_gate_threshold"] = float(overrides["confidence_gate_threshold"])
        except (TypeError, ValueError):
            pass

    parsed = dict(next_state.get("parsed_requirements") or {})
    if checkpoint_type == CheckpointType.CONFIRM_REQUIREMENTS:
        for key in ("product_type", "search_queries", "certifications_needed"):
            if key in overrides:
                parsed[key] = overrides[key]
    if checkpoint_type == CheckpointType.REVIEW_SUPPLIERS:
        if "minimum_supplier_count" in overrides:
            parsed["minimum_supplier_count"] = overrides["minimum_supplier_count"]
    if checkpoint_type == CheckpointType.ADJUST_WEIGHTS and "priority_tradeoff" in overrides:
        parsed["priority_tradeoff"] = overrides["priority_tradeoff"]

    if parsed:
        next_state["parsed_requirements"] = parsed

    # Routing stage after checkpoint
    stage_after = {
        CheckpointType.CONFIRM_REQUIREMENTS: "discovering",
        CheckpointType.REVIEW_SUPPLIERS: "verifying",
        CheckpointType.SET_CONFIDENCE_GATE: "comparing",
        CheckpointType.ADJUST_WEIGHTS: "recommending",
        CheckpointType.OUTREACH_PREFERENCES: "outreaching" if state.get("auto_outreach_enabled") else "complete",
    }
    next_state["current_stage"] = stage_after[checkpoint_type]

    return next_state
