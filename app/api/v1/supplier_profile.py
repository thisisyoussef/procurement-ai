"""Supplier profile aggregation endpoint.

Combines data from all pipeline stages (discovery, verification, comparison,
recommendation, outreach, communication) into a single supplier-centric response.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthUser, get_current_auth_user
from app.schemas.supplier_profile import (
    SupplierProfileAssessment,
    SupplierProfileCommMessage,
    SupplierProfileCompanyDetails,
    SupplierProfileHeroStats,
    SupplierProfileOutreachStatus,
    SupplierProfileQuote,
    SupplierProfileResponse,
    SupplierProfileVerification,
    SupplierProfileVerificationCheck,
)
from app.services.project_store import StoreUnavailableError, get_project_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/supplier", tags=["supplier-profile"])


# ── Helpers ────────────────────────────────────────────────────


async def _get_project_or_404(project_id: str) -> dict:
    store = get_project_store()
    try:
        project = await store.get_project(project_id)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _enforce_ownership(project: dict, user: AuthUser) -> None:
    if str(project.get("user_id")) != str(user.user_id):
        raise HTTPException(status_code=403, detail="Forbidden")


def _find_by_index(items: list[dict] | None, supplier_index: int, key: str = "supplier_index") -> dict | None:
    """Find a dict in a list where dict[key] == supplier_index."""
    if not items:
        return None
    for item in items:
        if item.get(key) == supplier_index:
            return item
    return None


def _extract_images(supplier: dict) -> list[str]:
    """Pull image URLs from raw_data."""
    raw = supplier.get("raw_data") or {}
    urls: list[str] = []

    for field in ("images", "image_urls", "product_images"):
        val = raw.get(field)
        if isinstance(val, list):
            urls.extend(v for v in val if isinstance(v, str) and v.startswith("http"))

    for field in ("product_image", "image_url", "thumbnail"):
        val = raw.get(field)
        if isinstance(val, str) and val.startswith("http"):
            urls.append(val)

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _derive_response_time(messages: list[dict], supplier_index: int) -> float | None:
    """Compute hours between first outbound and first inbound message for this supplier."""
    outbound_ts: float | None = None
    inbound_ts: float | None = None

    for msg in sorted(messages, key=lambda m: m.get("created_at", 0)):
        if msg.get("supplier_index") != supplier_index:
            continue
        if msg.get("direction") == "outbound" and outbound_ts is None:
            outbound_ts = msg.get("created_at")
        if msg.get("direction") == "inbound" and inbound_ts is None:
            inbound_ts = msg.get("created_at")
        if outbound_ts is not None and inbound_ts is not None:
            break

    if outbound_ts and inbound_ts and inbound_ts > outbound_ts:
        return round((inbound_ts - outbound_ts) / 3600, 1)
    return None


# ── Endpoint ───────────────────────────────────────────────────


@router.get("/{supplier_index}/profile", response_model=SupplierProfileResponse)
async def get_supplier_profile(
    project_id: str,
    supplier_index: int,
    current_user: AuthUser = Depends(get_current_auth_user),
) -> SupplierProfileResponse:
    project = await _get_project_or_404(project_id)
    _enforce_ownership(project, current_user)

    # ── Discovery (required) ──────────────────────────────────
    discovery = project.get("discovery_results") or {}
    suppliers = discovery.get("suppliers") or []

    if supplier_index < 0 or supplier_index >= len(suppliers):
        raise HTTPException(status_code=404, detail="Supplier not found at given index")

    supplier = suppliers[supplier_index]

    # ── Verification ──────────────────────────────────────────
    verification_data = project.get("verification_results") or {}
    verifications = verification_data.get("verifications") or []
    veri = _find_by_index(verifications, supplier_index)

    # ── Comparison ────────────────────────────────────────────
    comparison_data = project.get("comparison_result") or {}
    comparisons = comparison_data.get("comparisons") or []
    comp = _find_by_index(comparisons, supplier_index)

    # ── Recommendation ────────────────────────────────────────
    recommendation_data = project.get("recommendation_result") or {}
    recommendations = recommendation_data.get("recommendations") or []
    rec = _find_by_index(recommendations, supplier_index)

    # ── Outreach ──────────────────────────────────────────────
    outreach_state = project.get("outreach_state") or {}
    supplier_statuses = outreach_state.get("supplier_statuses") or []
    outreach_status = _find_by_index(supplier_statuses, supplier_index)

    parsed_quotes = outreach_state.get("parsed_quotes") or []
    parsed_quote = _find_by_index(parsed_quotes, supplier_index)

    # ── Communication messages ────────────────────────────────
    comm_monitor = outreach_state.get("communication_monitor") or {}
    all_messages = comm_monitor.get("messages") or []
    supplier_messages = [m for m in all_messages if m.get("supplier_index") == supplier_index]
    supplier_messages.sort(key=lambda m: m.get("created_at", 0), reverse=True)

    # ── Build hero stats ──────────────────────────────────────
    # Prefer quoted price over estimate
    unit_price = None
    price_source = "estimate"
    if parsed_quote and parsed_quote.get("unit_price"):
        unit_price = parsed_quote["unit_price"]
        price_source = "quoted"
    elif comp and comp.get("estimated_unit_price"):
        unit_price = comp["estimated_unit_price"]
        price_source = "estimate"

    moq = None
    if parsed_quote and parsed_quote.get("moq"):
        moq = parsed_quote["moq"]
    elif comp and comp.get("moq"):
        moq = comp["moq"]

    lead_time = None
    if parsed_quote and parsed_quote.get("lead_time"):
        lead_time = parsed_quote["lead_time"]
    elif comp and comp.get("lead_time"):
        lead_time = comp["lead_time"]

    hero_stats = SupplierProfileHeroStats(
        unit_price=unit_price,
        unit_price_source=price_source,
        moq=moq,
        lead_time=lead_time,
        google_rating=supplier.get("google_rating"),
        google_review_count=supplier.get("google_review_count"),
        response_time_hours=_derive_response_time(all_messages, supplier_index),
    )

    # ── Build quote section ───────────────────────────────────
    quote = None
    if parsed_quote:
        quantity = (project.get("parsed_requirements") or {}).get("quantity")
        quote = SupplierProfileQuote(
            unit_price=parsed_quote.get("unit_price"),
            currency=parsed_quote.get("currency", "USD"),
            moq=parsed_quote.get("moq"),
            lead_time=parsed_quote.get("lead_time"),
            payment_terms=parsed_quote.get("payment_terms"),
            shipping_terms=parsed_quote.get("shipping_terms"),
            validity_period=parsed_quote.get("validity_period"),
            notes=parsed_quote.get("notes"),
            source="parsed_response",
            confidence_score=parsed_quote.get("confidence_score", 0),
            quantity=quantity,
        )
    elif comp and comp.get("estimated_unit_price"):
        quantity = (project.get("parsed_requirements") or {}).get("quantity")
        quote = SupplierProfileQuote(
            unit_price=comp.get("estimated_unit_price"),
            currency="USD",
            moq=comp.get("moq"),
            lead_time=comp.get("lead_time"),
            source="estimate",
            confidence_score=0,
            quantity=quantity,
        )

    # ── Build assessment ──────────────────────────────────────
    assessment = None
    if rec:
        assessment = SupplierProfileAssessment(
            reasoning=rec.get("reasoning", ""),
            confidence=rec.get("confidence", "low"),
            best_for=rec.get("best_for", ""),
            rank=rec.get("rank"),
            overall_score=rec.get("overall_score", 0),
            strengths=(comp or {}).get("strengths", []),
            weaknesses=(comp or {}).get("weaknesses", []),
        )

    # ── Build verification ────────────────────────────────────
    verification = None
    if veri:
        checks = [
            SupplierProfileVerificationCheck(
                check_type=c.get("check_type", ""),
                status=c.get("status", "unavailable"),
                score=c.get("score", 0),
                details=c.get("details", ""),
            )
            for c in (veri.get("checks") or [])
        ]
        verification = SupplierProfileVerification(
            composite_score=veri.get("composite_score", 0),
            risk_level=veri.get("risk_level", "unknown"),
            recommendation=veri.get("recommendation", "pending"),
            summary=veri.get("summary", ""),
            checks=checks,
        )

    # ── Build company details ─────────────────────────────────
    enrichment = supplier.get("enrichment") or {}
    company = SupplierProfileCompanyDetails(
        address=supplier.get("address"),
        city=supplier.get("city"),
        country=supplier.get("country"),
        website=supplier.get("website"),
        email=enrichment.get("best_email") or supplier.get("email"),
        phone=enrichment.get("best_phone") or supplier.get("phone"),
        preferred_contact_method=(veri or {}).get("preferred_contact_method", "email"),
        language=supplier.get("language_discovered"),
        categories=supplier.get("categories", []),
        certifications=supplier.get("certifications", []),
        source=supplier.get("source", "unknown"),
        is_intermediary=supplier.get("is_intermediary", False),
    )

    # ── Build outreach status ─────────────────────────────────
    outreach = None
    if outreach_status:
        outreach = SupplierProfileOutreachStatus(
            email_sent=outreach_status.get("email_sent", False),
            response_received=outreach_status.get("response_received", False),
            delivery_status=outreach_status.get("delivery_status", "unknown"),
            follow_ups_sent=outreach_status.get("follow_ups_sent", 0),
            excluded=outreach_status.get("excluded", False),
            exclusion_reason=outreach_status.get("exclusion_reason"),
        )

    # ── Build communication log ───────────────────────────────
    communication_log = [
        SupplierProfileCommMessage(
            message_key=m.get("message_key", ""),
            direction=m.get("direction", "outbound"),
            channel=m.get("channel", "email"),
            subject=m.get("subject"),
            body_preview=m.get("body_preview"),
            delivery_status=m.get("delivery_status", "unknown"),
            created_at=m.get("created_at", 0),
            source=m.get("source"),
        )
        for m in supplier_messages
    ]

    # ── Score breakdown ───────────────────────────────────────
    score_breakdown = None
    if comp:
        score_breakdown = {
            "price_score": comp.get("price_score", 0),
            "quality_score": comp.get("quality_score", 0),
            "shipping_score": comp.get("shipping_score", 0),
            "review_score": comp.get("review_score", 0),
            "lead_time_score": comp.get("lead_time_score", 0),
        }

    return SupplierProfileResponse(
        supplier_index=supplier_index,
        name=supplier.get("name", "Unknown Supplier"),
        description=supplier.get("description"),
        hero_stats=hero_stats,
        quote=quote,
        assessment=assessment,
        verification=verification,
        company=company,
        outreach=outreach,
        communication_log=communication_log,
        images=_extract_images(supplier),
        score_breakdown=score_breakdown,
    )
