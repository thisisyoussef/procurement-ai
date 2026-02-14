"""Outreach API endpoints — manage RFQ emails, responses, and follow-ups."""

import logging
import re
import time
import traceback
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from app.agents.followup_agent import generate_follow_ups
from app.agents.outreach_agent import draft_outreach_emails
from app.agents.response_parser import parse_supplier_response
from app.core.config import get_settings
from app.core.email_service import build_rfq_html, send_email
from app.schemas.agent_state import (
    AutoOutreachConfig,
    DiscoveredSupplier,
    DiscoveryResults,
    OutreachEvent,
    OutreachPlanStep,
    OutreachState,
    ParsedRequirements,
    RecommendationResult,
    SupplierOutreachPlan,
    SupplierOutreachStatus,
    VerificationResults,
)
from app.schemas.project import (
    OutreachCancelPendingRequest,
    EmailApprovalRequest,
    OutreachQuickApprovalRequest,
    OutreachRetryFailedRequest,
    OutreachStartRequest,
    QuoteParseRequest,
)
from app.core.auth import AuthUser, get_current_auth_user
from app.services.project_store import StoreUnavailableError, get_project_store
from app.services.communication_monitor import (
    ensure_monitor,
    mark_inbound_message_parsed,
    record_inbound_email,
    record_inbox_check,
    record_outbound_email,
    set_owner_email,
)
from app.services.project_contact import resolve_project_owner_email
from app.services.supplier_memory import (
    record_supplier_interaction,
    record_supplier_interactions,
)
from app.services.project_events import record_project_event
from app.core.database import async_session_factory
from app.repositories.user_repository import get_user_by_id

logger = logging.getLogger(__name__)
settings = get_settings()


async def _fetch_business_profile(user_id: str) -> dict[str, str | None] | None:
    """Load the user's business profile for email personalization."""
    try:
        async with async_session_factory() as session:
            user = await get_user_by_id(session, user_id)
    except Exception:
        logger.warning("Failed to load business profile for user %s", user_id, exc_info=True)
        return None

    if user is None or not user.onboarding_completed:
        return None

    return {
        "company_name": user.company_name,
        "contact_name": user.full_name,
        "job_title": user.job_title,
        "email": user.email,
        "phone": user.phone,
        "company_website": user.company_website,
        "business_address": user.business_address,
        "company_description": user.company_description,
    }

router = APIRouter(prefix="/projects/{project_id}/outreach", tags=["outreach"])

UNFULFILLMENT_PATTERNS = [
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bunable to\b",
    r"\bdo not manufacture\b",
    r"\bdo not produce\b",
    r"\boutside our capability\b",
    r"\bnot able to\b",
    r"\bwe don't offer\b",
    r"\bcan't meet\b",
]


async def _get_project(project_id: str, current_user: AuthUser) -> dict:
    store = get_project_store()
    try:
        project = await store.get_project(project_id)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project.get("user_id")) != str(current_user.user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return project


async def _save_project(project: dict) -> None:
    store = get_project_store()
    try:
        await store.save_project(project)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


def _get_outreach_state(project: dict) -> OutreachState:
    raw = project.get("outreach_state")
    if not raw:
        raise HTTPException(status_code=400, detail="No outreach started for this project")
    return OutreachState(**raw) if isinstance(raw, dict) else raw


def _owner_email_from_user(current_user: AuthUser | None) -> str | None:
    if not current_user:
        return None
    email = (current_user.email or "").strip().lower()
    return email or None


def _cc_list(owner_email: str | None) -> list[str]:
    return [owner_email] if owner_email else []


def _set_supplier_delivery_success(status: SupplierOutreachStatus, email_id: str) -> None:
    status.email_sent = True
    status.sent_at = time.time()
    status.email_id = email_id
    if email_id and email_id not in status.email_ids:
        status.email_ids.append(email_id)
    status.delivery_status = "sent"
    status.send_error = None


def _set_supplier_delivery_failure(status: SupplierOutreachStatus, reason: str) -> None:
    status.email_sent = False
    status.delivery_status = "failed"
    status.send_error = reason


def _match_supplier_index_from_token(
    outreach: OutreachState,
    discovery: DiscoveryResults,
    matched_token: str | None,
) -> tuple[int | None, str | None]:
    if not matched_token:
        return None, None
    token = matched_token.lower()
    for supplier_status in outreach.supplier_statuses:
        if supplier_status.excluded or supplier_status.response_received:
            continue
        idx = supplier_status.supplier_index
        if not (0 <= idx < len(discovery.suppliers)):
            continue
        supplier = discovery.suppliers[idx]
        if supplier.email and supplier.email.lower() in token:
            return idx, supplier.name
        if supplier.website:
            from urllib.parse import urlparse

            try:
                domain = urlparse(supplier.website).netloc.replace("www.", "").lower()
            except Exception:  # noqa: BLE001
                domain = ""
            if domain and domain in token:
                return idx, supplier.name
    return None, None


async def _send_and_track_email(
    *,
    project: dict,
    outreach: OutreachState,
    supplier_index: int,
    supplier_name: str,
    recipient: str,
    subject: str,
    body: str,
    source_label: str,
    owner_email: str | None,
) -> dict:
    set_owner_email(outreach, owner_email)
    cc = _cc_list(owner_email)
    body_html = build_rfq_html(body)
    result = await send_email(
        to=recipient,
        subject=subject,
        body_html=body_html,
        cc=cc,
        reply_to=settings.from_email,
        headers={"X-Tamkin-Project-ID": str(project.get("id", ""))},
    )

    if result.get("sent"):
        email_id = result.get("id", "")
        record_outbound_email(
            outreach,
            supplier_index=supplier_index,
            supplier_name=supplier_name,
            to_email=recipient,
            from_email=result.get("from") or settings.from_email,
            cc_emails=result.get("cc") or cc,
            subject=subject,
            body=body,
            resend_email_id=email_id,
            delivery_status="sent",
            source=source_label,
            event_type="email_sent",
            details={
                "project_id": project.get("id"),
                "provider": result.get("provider", "resend"),
                "from_email": result.get("from"),
                "to_email": result.get("to") or recipient,
                "cc_emails": result.get("cc") or cc,
            },
        )
    else:
        error_detail = {
            "error": result.get("error", "unknown"),
            "error_type": result.get("error_type"),
            "provider": result.get("provider", "resend"),
            "from_email": result.get("from") or settings.from_email,
            "to_email": result.get("to") or recipient,
            "cc_emails": result.get("cc") or cc,
        }
        provider_response = result.get("provider_response")
        if provider_response is not None:
            error_detail["provider_response"] = provider_response
        record_outbound_email(
            outreach,
            supplier_index=supplier_index,
            supplier_name=supplier_name,
            to_email=recipient,
            from_email=settings.from_email,
            cc_emails=cc,
            subject=subject,
            body=body,
            resend_email_id=None,
            delivery_status="failed",
            source=source_label,
            event_type="send_failed",
            details={
                "project_id": project.get("id"),
                **error_detail,
            },
        )
    return result


def _append_event(
    outreach: OutreachState,
    event_type: str,
    supplier_index: int | None = None,
    supplier_name: str | None = None,
    **details,
) -> None:
    outreach.events.append(
        OutreachEvent(
            event_type=event_type,
            supplier_index=supplier_index,
            supplier_name=supplier_name,
            details=details,
        )
    )


def _response_indicates_cannot_fulfill(quote_text: str | None, response_text: str) -> bool:
    text = f"{quote_text or ''}\n{response_text}".lower()
    return any(re.search(pattern, text) for pattern in UNFULFILLMENT_PATTERNS)


def _apply_supplier_exclusion(
    project: dict,
    outreach: OutreachState,
    supplier_index: int,
    supplier_name: str,
    reason: str,
) -> None:
    already_excluded = supplier_index in outreach.excluded_suppliers
    if not already_excluded:
        outreach.excluded_suppliers.append(supplier_index)

    for status in outreach.supplier_statuses:
        if status.supplier_index == supplier_index:
            status.excluded = True
            status.exclusion_reason = reason
            break

    discovery_data = project.get("discovery_results")
    if discovery_data and 0 <= supplier_index < len(discovery_data.get("suppliers", [])):
        supplier = discovery_data["suppliers"][supplier_index]
        supplier["filtered_reason"] = "unable_to_fulfill"

    comparison = project.get("comparison_result")
    if comparison and comparison.get("comparisons"):
        comparison["comparisons"] = [
            c
            for c in comparison["comparisons"]
            if c.get("supplier_index") != supplier_index
        ]
        project["comparison_result"] = comparison

    recommendation = project.get("recommendation_result")
    if recommendation and recommendation.get("recommendations"):
        kept = [
            r
            for r in recommendation["recommendations"]
            if r.get("supplier_index") != supplier_index
        ]
        for rank, item in enumerate(kept, start=1):
            item["rank"] = rank
        recommendation["recommendations"] = kept
        project["recommendation_result"] = recommendation

    if not already_excluded:
        _append_event(
            outreach,
            "supplier_excluded",
            supplier_index=supplier_index,
            supplier_name=supplier_name,
            reason=reason,
        )


def _normalize_draft_supplier_indices(drafts, selected_indices: list[int]) -> None:
    for draft in drafts:
        local_idx = draft.supplier_index
        if 0 <= local_idx < len(selected_indices):
            draft.supplier_index = selected_indices[local_idx]


def _resolve_draft_recipient(
    draft,
    discovery: DiscoveryResults,
) -> str | None:
    recipient = draft.recipient_email
    if recipient:
        return recipient
    idx = draft.supplier_index
    if 0 <= idx < len(discovery.suppliers):
        return discovery.suppliers[idx].email
    return None


def _get_selected_suppliers_for_quick_approval(
    recs: RecommendationResult,
    discovery: DiscoveryResults,
    outreach: OutreachState,
    max_suppliers: int,
    requested_indices: list[int] | None = None,
) -> tuple[list[int], list[DiscoveredSupplier]]:
    selected_indices: list[int] = []
    selected_suppliers: list[DiscoveredSupplier] = []

    if requested_indices:
        for idx in requested_indices:
            if idx in outreach.excluded_suppliers:
                continue
            if not (0 <= idx < len(discovery.suppliers)):
                continue
            if idx in selected_indices:
                continue
            selected_indices.append(idx)
            selected_suppliers.append(discovery.suppliers[idx])
            if len(selected_indices) >= max_suppliers:
                break
        if selected_suppliers:
            return selected_indices, selected_suppliers

    for rec in sorted(recs.recommendations, key=lambda r: r.rank):
        idx = rec.supplier_index
        if idx in outreach.excluded_suppliers:
            continue
        if not (0 <= idx < len(discovery.suppliers)):
            continue
        if idx in selected_indices:
            continue
        selected_indices.append(idx)
        selected_suppliers.append(discovery.suppliers[idx])
        if len(selected_indices) >= max_suppliers:
            break

    return selected_indices, selected_suppliers


def _get_or_create_supplier_status(
    outreach: OutreachState,
    supplier_index: int,
    supplier_name: str,
) -> SupplierOutreachStatus:
    for status in outreach.supplier_statuses:
        if status.supplier_index == supplier_index:
            return status
    status = SupplierOutreachStatus(
        supplier_name=supplier_name,
        supplier_index=supplier_index,
    )
    outreach.supplier_statuses.append(status)
    return status


async def _draft_and_send_initial_outreach(
    *,
    project: dict,
    outreach: OutreachState,
    reqs: ParsedRequirements,
    recs: RecommendationResult,
    selected_indices: list[int],
    selected_suppliers: list[DiscoveredSupplier],
    source_label: str,
    owner_email: str | None,
    business_profile: dict[str, str | None] | None = None,
) -> dict:
    set_owner_email(outreach, owner_email)
    ensure_monitor(outreach, owner_email=owner_email)
    draft_result = await draft_outreach_emails(selected_suppliers, reqs, recs, business_profile=business_profile)
    _normalize_draft_supplier_indices(draft_result.drafts, selected_indices)
    drafts_by_index = {d.supplier_index: d for d in draft_result.drafts}

    existing_drafts_by_index = {d.supplier_index: d for d in outreach.draft_emails}
    existing_drafts_by_index.update(drafts_by_index)
    outreach.draft_emails = list(existing_drafts_by_index.values())

    sent_count = 0
    failed_count = 0

    for idx, supplier in zip(selected_indices, selected_suppliers):
        if idx not in outreach.selected_suppliers:
            outreach.selected_suppliers.append(idx)

        status = _get_or_create_supplier_status(outreach, idx, supplier.name)
        draft = drafts_by_index.get(idx)
        plan = _build_supplier_plan(supplier, idx, reqs, None)
        _upsert_plan(outreach, plan)

        if not draft:
            failed_count += 1
            status.email_sent = False
            status.delivery_status = "failed"
            status.send_error = "Draft generation failed"
            _append_event(
                outreach,
                "send_failed",
                supplier_index=idx,
                supplier_name=supplier.name,
                reason="draft_missing",
                source=source_label,
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=idx,
                interaction_type="rfq_send_failed",
                source="outreach",
                details={"reason": "draft_missing", "entrypoint": source_label},
            )
            continue

        if draft.status == "sent" and status.email_sent:
            continue

        recipient = draft.recipient_email or supplier.email
        if not recipient:
            draft.status = "failed"
            failed_count += 1
            _set_supplier_delivery_failure(status, "No supplier email found")
            _append_event(
                outreach,
                "send_failed",
                supplier_index=idx,
                supplier_name=draft.supplier_name,
                reason="missing_email",
                source=source_label,
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=idx,
                interaction_type="rfq_send_failed",
                source="outreach",
                details={"reason": "missing_email", "entrypoint": source_label},
            )
            continue

        result = await _send_and_track_email(
            project=project,
            outreach=outreach,
            supplier_index=idx,
            supplier_name=draft.supplier_name,
            recipient=recipient,
            subject=draft.subject,
            body=draft.body,
            source_label=source_label,
            owner_email=owner_email,
        )
        if result.get("sent"):
            draft.status = "sent"
            sent_count += 1
            email_id = result.get("id", "")
            _set_supplier_delivery_success(status, email_id)
            _append_event(
                outreach,
                "email_sent",
                supplier_index=idx,
                supplier_name=draft.supplier_name,
                email_id=email_id,
                source=source_label,
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=idx,
                interaction_type="rfq_sent",
                source="outreach",
                details={
                    "email_id": email_id,
                    "recipient": recipient,
                    "cc_owner_email": owner_email,
                    "entrypoint": source_label,
                },
            )
        else:
            draft.status = "failed"
            failed_count += 1
            _set_supplier_delivery_failure(status, result.get("error", "unknown"))
            _append_event(
                outreach,
                "send_failed",
                supplier_index=idx,
                supplier_name=draft.supplier_name,
                reason=result.get("error", "unknown"),
                source=source_label,
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=idx,
                interaction_type="rfq_send_failed",
                source="outreach",
                details={
                    "reason": result.get("error", "unknown"),
                    "recipient": recipient,
                    "entrypoint": source_label,
                },
            )

    return {
        "sent_count": sent_count,
        "failed_count": failed_count,
        "selected_count": len(selected_indices),
    }


def _build_supplier_plan(
    supplier: DiscoveredSupplier,
    supplier_index: int,
    requirements: ParsedRequirements,
    recommendation_label: str | None,
) -> SupplierOutreachPlan:
    friction_risks: list[str] = []
    if not supplier.email:
        friction_risks.append("missing_direct_email")
    if not requirements.quantity:
        friction_risks.append("incomplete_quantity")
    if not requirements.delivery_location:
        friction_risks.append("missing_delivery_location")

    objective = f"Secure a valid quote for {requirements.product_type}"
    if recommendation_label:
        objective += f" ({recommendation_label})"

    steps = [
        OutreachPlanStep(stage="intent_capture", objective="Confirm buying intent and constraints", owner="buyer", due_in_hours=0),
        OutreachPlanStep(stage="rfq_send", objective="Send personalized RFQ with clear CTA", owner="system", due_in_hours=1),
        OutreachPlanStep(stage="delivery_check", objective="Validate delivery/open signal", owner="system", due_in_hours=6),
        OutreachPlanStep(stage="response_capture", objective="Capture and parse supplier response", owner="system", due_in_hours=48),
        OutreachPlanStep(stage="decision_support", objective=objective, owner="system", due_in_hours=72),
    ]

    return SupplierOutreachPlan(
        supplier_name=supplier.name,
        supplier_index=supplier_index,
        channel="email",
        friction_risks=friction_risks,
        steps=steps,
    )


def _upsert_plan(outreach: OutreachState, plan: SupplierOutreachPlan) -> None:
    for idx, existing in enumerate(outreach.supplier_plans):
        if existing.supplier_index == plan.supplier_index:
            outreach.supplier_plans[idx] = plan
            return
    outreach.supplier_plans.append(plan)


@router.post("/start")
async def start_outreach(
    project_id: str,
    request: OutreachStartRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Select suppliers and draft personalized RFQ emails."""
    project = await _get_project(project_id, current_user)
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email

    if not project.get("recommendation_result"):
        raise HTTPException(status_code=400, detail="Pipeline must complete before outreach")

    try:
        reqs = ParsedRequirements(**project["parsed_requirements"])
        discovery = DiscoveryResults(**project["discovery_results"])
        recs = RecommendationResult(**project["recommendation_result"])
        rec_by_idx = {r.supplier_index: r.best_for for r in recs.recommendations}

        selected: list[DiscoveredSupplier] = []
        selected_indices: list[int] = []
        for idx in request.supplier_indices:
            if 0 <= idx < len(discovery.suppliers):
                selected.append(discovery.suppliers[idx])
                selected_indices.append(idx)

        if not selected:
            raise HTTPException(status_code=400, detail="No valid supplier indices provided")

        business_profile = await _fetch_business_profile(current_user.user_id)
        result = await draft_outreach_emails(selected, reqs, recs, business_profile=business_profile)
        _normalize_draft_supplier_indices(result.drafts, selected_indices)

        supplier_statuses = [SupplierOutreachStatus(supplier_name=s.name, supplier_index=idx) for idx, s in zip(selected_indices, selected)]

        outreach = OutreachState(
            selected_suppliers=selected_indices,
            supplier_statuses=supplier_statuses,
            draft_emails=result.drafts,
        )
        set_owner_email(outreach, owner_email)
        ensure_monitor(outreach, owner_email=owner_email)

        _append_event(outreach, "intent_registered", details={"selected_suppliers": len(selected_indices)})
        for idx, supplier in zip(selected_indices, selected):
            plan = _build_supplier_plan(supplier, idx, reqs, rec_by_idx.get(idx))
            _upsert_plan(outreach, plan)
            _append_event(outreach, "outreach_planned", supplier_index=idx, supplier_name=supplier.name, friction_risks=plan.friction_risks)

        project["outreach_state"] = outreach.model_dump(mode="json")
        await record_supplier_interactions(
            project=project,
            supplier_indices=selected_indices,
            interaction_type="selected_for_outreach",
            source="outreach",
            details={"entrypoint": "manual_start"},
        )
        await record_project_event(
            project,
            event_type="outreach_drafted",
            title="Outreach drafts ready",
            description=f"Drafted outreach for {len(selected_indices)} supplier(s).",
            priority="info",
            phase="outreach",
            payload={"selected_count": len(selected_indices), "entrypoint": "manual_start"},
        )

        await _save_project(project)
        return {"drafts": [d.model_dump() for d in result.drafts], "summary": result.summary}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Outreach start failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-approval")
async def quick_outreach_approval(
    project_id: str,
    request: OutreachQuickApprovalRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Single yes/no outreach flow: approve and auto-send, or decline."""
    project = await _get_project(project_id, current_user)

    if not project.get("recommendation_result"):
        raise HTTPException(status_code=400, detail="Comparison must complete before outreach")

    raw = project.get("outreach_state")
    outreach = OutreachState(**raw) if isinstance(raw, dict) else (raw or OutreachState())
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    set_owner_email(outreach, owner_email)

    if not request.approve:
        outreach.quick_approval_decision = "declined"
        _append_event(outreach, "quick_outreach_declined")
        project["outreach_state"] = outreach.model_dump(mode="json")
        await record_project_event(
            project,
            event_type="outreach_declined",
            title="Outreach skipped",
            description="You declined outreach for now.",
            priority="medium",
            phase="outreach",
        )
        await _save_project(project)
        return {"status": "declined"}

    reqs = ParsedRequirements(**project["parsed_requirements"])
    discovery = DiscoveryResults(**project["discovery_results"])
    recs = RecommendationResult(**project["recommendation_result"])

    selected_indices, selected_suppliers = _get_selected_suppliers_for_quick_approval(
        recs=recs,
        discovery=discovery,
        outreach=outreach,
        max_suppliers=request.max_suppliers,
        requested_indices=request.supplier_indices,
    )
    if not selected_suppliers:
        raise HTTPException(status_code=400, detail="No eligible suppliers available for outreach")

    business_profile = await _fetch_business_profile(current_user.user_id)

    batch_result = await _draft_and_send_initial_outreach(
        project=project,
        outreach=outreach,
        reqs=reqs,
        recs=recs,
        selected_indices=selected_indices,
        selected_suppliers=selected_suppliers,
        source_label="quick_approval",
        owner_email=owner_email,
        business_profile=business_profile,
    )

    outreach.quick_approval_decision = "approved"
    _append_event(
        outreach,
        "quick_outreach_approved",
        sent_count=batch_result["sent_count"],
        failed_count=batch_result["failed_count"],
        selected_suppliers=batch_result["selected_count"],
    )

    project["outreach_state"] = outreach.model_dump(mode="json")
    await record_project_event(
        project,
        event_type="outreach_sent",
        title="Outreach sent",
        description=(
            f"Sent outreach to {batch_result['sent_count']} supplier(s); "
            f"{batch_result['failed_count']} failed."
        ),
        priority="info",
        phase="outreach",
        payload=batch_result,
    )
    await _save_project(project)

    return {
        "status": "approved",
        "sent_count": batch_result["sent_count"],
        "failed_count": batch_result["failed_count"],
        "selected_suppliers": selected_indices,
    }


@router.post("/retry-failed")
async def retry_failed_outreach(
    project_id: str,
    request: OutreachRetryFailedRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Retry failed outreach sends for selected or all suppliers."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    set_owner_email(outreach, owner_email)

    discovery = DiscoveryResults(**project["discovery_results"])
    requested_indices = set(request.supplier_indices or [])
    retry_targets = []
    for draft in outreach.draft_emails:
        if requested_indices and draft.supplier_index not in requested_indices:
            continue
        if draft.status != "failed":
            continue
        supplier_status = _get_or_create_supplier_status(
            outreach=outreach,
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
        )
        if supplier_status.excluded:
            continue
        retry_targets.append((draft, supplier_status))

    if not retry_targets:
        return {
            "status": "nothing_to_retry",
            "retried_count": 0,
            "sent_count": 0,
            "failed_count": 0,
        }

    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for draft, supplier_status in retry_targets:
        recipient = _resolve_draft_recipient(draft, discovery)
        if not recipient:
            failed_count += 1
            _set_supplier_delivery_failure(supplier_status, "No supplier email found")
            _append_event(
                outreach,
                "retry_failed",
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                reason="missing_email",
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=draft.supplier_index,
                interaction_type="rfq_retry_failed",
                source="outreach",
                details={"reason": "missing_email"},
            )
            continue

        _append_event(
            outreach,
            "retry_attempted",
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
            recipient=recipient,
        )
        result = await _send_and_track_email(
            project=project,
            outreach=outreach,
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
            recipient=recipient,
            subject=draft.subject,
            body=draft.body,
            source_label="retry_failed",
            owner_email=owner_email,
        )
        if result.get("sent"):
            draft.status = "sent"
            sent_count += 1
            _set_supplier_delivery_success(supplier_status, result.get("id", ""))
            _append_event(
                outreach,
                "email_sent",
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                email_id=result.get("id", ""),
                source="retry_failed",
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=draft.supplier_index,
                interaction_type="rfq_retried_sent",
                source="outreach",
                details={
                    "email_id": result.get("id", ""),
                    "recipient": recipient,
                    "cc_owner_email": owner_email,
                },
            )
        else:
            failed_count += 1
            draft.status = "failed"
            _set_supplier_delivery_failure(supplier_status, result.get("error", "unknown"))
            _append_event(
                outreach,
                "retry_failed",
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                reason=result.get("error", "unknown"),
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=draft.supplier_index,
                interaction_type="rfq_retry_failed",
                source="outreach",
                details={
                    "reason": result.get("error", "unknown"),
                    "recipient": recipient,
                },
            )

    project["outreach_state"] = outreach.model_dump(mode="json")
    await record_project_event(
        project,
        event_type="outreach_retry_attempted",
        title="Retried failed outreach sends",
        description=(
            f"Retried {len(retry_targets)} failed draft(s): "
            f"{sent_count} sent, {failed_count} still failed."
        ),
        priority="medium",
        phase="outreach",
        payload={
            "retried_count": len(retry_targets),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
        },
    )
    await _save_project(project)
    return {
        "status": "processed",
        "retried_count": len(retry_targets),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
    }


@router.post("/cancel-pending")
async def cancel_pending_outreach(
    project_id: str,
    request: OutreachCancelPendingRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Cancel pending or queued outreach sends before they are sent."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    requested_indices = set(request.supplier_indices or [])

    cancelable_statuses = {"draft", "auto_queued"}
    canceled = 0
    skipped = 0
    canceled_indices: list[int] = []

    for draft in outreach.draft_emails:
        if requested_indices and draft.supplier_index not in requested_indices:
            continue
        if draft.status not in cancelable_statuses:
            skipped += 1
            continue

        supplier_status = _get_or_create_supplier_status(
            outreach=outreach,
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
        )
        draft.status = "canceled"
        supplier_status.delivery_status = "canceled"
        supplier_status.send_error = "Canceled by user"
        canceled += 1
        canceled_indices.append(draft.supplier_index)
        _append_event(
            outreach,
            "send_canceled",
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
            reason="canceled_by_user",
        )
        await record_supplier_interaction(
            project=project,
            supplier_index=draft.supplier_index,
            interaction_type="rfq_canceled",
            source="outreach",
            details={"reason": "canceled_by_user"},
        )

    if canceled:
        project["outreach_state"] = outreach.model_dump(mode="json")
        await record_project_event(
            project,
            event_type="outreach_pending_canceled",
            title="Pending outreach canceled",
            description=f"Canceled {canceled} pending outreach draft(s).",
            priority="medium",
            phase="outreach",
            payload={"canceled": canceled, "skipped": skipped, "supplier_indices": canceled_indices},
        )
        await _save_project(project)

    return {
        "status": "processed" if canceled else "nothing_to_cancel",
        "canceled_count": canceled,
        "skipped_count": skipped,
        "supplier_indices": canceled_indices,
    }


@router.post("/approve/{draft_index}")
async def approve_and_send(
    project_id: str,
    draft_index: int,
    request: EmailApprovalRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Approve (optionally edit) and send a draft email."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    set_owner_email(outreach, owner_email)

    if draft_index < 0 or draft_index >= len(outreach.draft_emails):
        raise HTTPException(status_code=400, detail="Invalid draft index")

    draft = outreach.draft_emails[draft_index]
    supplier_status = _get_or_create_supplier_status(
        outreach=outreach,
        supplier_index=draft.supplier_index,
        supplier_name=draft.supplier_name,
    )

    if supplier_status.excluded:
        raise HTTPException(status_code=400, detail="Supplier was removed from outreach")

    if request.edited_subject:
        draft.subject = request.edited_subject
    if request.edited_body:
        draft.body = request.edited_body

    _append_event(outreach, "draft_approved", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name)

    recipient = draft.recipient_email
    if not recipient:
        discovery = DiscoveryResults(**project["discovery_results"])
        if draft.supplier_index < len(discovery.suppliers):
            recipient = discovery.suppliers[draft.supplier_index].email

    if not recipient:
        draft.status = "failed"
        _set_supplier_delivery_failure(supplier_status, "No supplier email found")
        _append_event(outreach, "send_failed", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, reason="missing_email")
        await record_supplier_interaction(
            project=project,
            supplier_index=draft.supplier_index,
            interaction_type="rfq_send_failed",
            source="outreach",
            details={"reason": "missing_email"},
        )
        await record_project_event(
            project,
            event_type="outreach_send_failed",
            title="Outreach send failed",
            description=f"No email found for {draft.supplier_name}.",
            priority="high",
            phase="outreach",
            payload={"supplier_index": draft.supplier_index, "reason": "missing_email"},
        )
        record_outbound_email(
            outreach,
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
            to_email=None,
            from_email=settings.from_email,
            cc_emails=_cc_list(owner_email),
            subject=draft.subject,
            body=draft.body,
            resend_email_id=None,
            delivery_status="failed",
            source="manual_approve",
            event_type="send_failed",
            details={"reason": "missing_email"},
        )
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)
        return {"sent": False, "error": f"No email address found for {draft.supplier_name}. You'll need to provide one."}

    _append_event(outreach, "send_attempted", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, recipient=recipient)
    result = await _send_and_track_email(
        project=project,
        outreach=outreach,
        supplier_index=draft.supplier_index,
        supplier_name=draft.supplier_name,
        recipient=recipient,
        subject=draft.subject,
        body=draft.body,
        source_label="manual_approve",
        owner_email=owner_email,
    )

    if result.get("sent"):
        draft.status = "sent"
        email_id = result.get("id", "")
        _set_supplier_delivery_success(supplier_status, email_id)
        _append_event(outreach, "email_sent", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, email_id=email_id)
        await record_supplier_interaction(
            project=project,
            supplier_index=draft.supplier_index,
            interaction_type="rfq_sent",
            source="outreach",
            details={"email_id": email_id, "recipient": recipient, "cc_owner_email": owner_email},
        )
        await record_project_event(
            project,
            event_type="outreach_email_sent",
            title="Outreach email sent",
            description=f"Sent outreach to {draft.supplier_name}.",
            priority="info",
            phase="outreach",
            payload={"supplier_index": draft.supplier_index, "email_id": email_id},
        )
    else:
        draft.status = "failed"
        _set_supplier_delivery_failure(supplier_status, result.get("error", "unknown"))
        _append_event(outreach, "send_failed", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, reason=result.get("error", "unknown"))
        await record_supplier_interaction(
            project=project,
            supplier_index=draft.supplier_index,
            interaction_type="rfq_send_failed",
            source="outreach",
            details={"reason": result.get("error", "unknown"), "recipient": recipient},
        )
        await record_project_event(
            project,
            event_type="outreach_send_failed",
            title="Outreach send failed",
            description=f"Send failed for {draft.supplier_name}: {result.get('error', 'unknown')}",
            priority="high",
            phase="outreach",
            payload={"supplier_index": draft.supplier_index, "reason": result.get("error", "unknown")},
        )

    project["outreach_state"] = outreach.model_dump(mode="json")

    await _save_project(project)

    return {"sent": result.get("sent", False), "error": result.get("error"), "supplier_name": draft.supplier_name}


@router.post("/parse-response")
async def parse_response(
    project_id: str,
    request: QuoteParseRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Parse a pasted supplier response into structured quote data."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)

    reqs = ParsedRequirements(**project["parsed_requirements"])
    discovery = DiscoveryResults(**project["discovery_results"])

    if request.supplier_index >= len(discovery.suppliers):
        raise HTTPException(status_code=400, detail="Invalid supplier index")

    supplier = discovery.suppliers[request.supplier_index]

    try:
        quote = await parse_supplier_response(
            supplier_name=supplier.name,
            supplier_index=request.supplier_index,
            response_text=request.response_text,
            requirements=reqs,
        )

        outreach.parsed_quotes.append(quote)

        for status in outreach.supplier_statuses:
            if status.supplier_index == request.supplier_index:
                status.response_received = True
                status.response_text = request.response_text
                status.parsed_quote = quote
                break

        if quote.can_fulfill is False or _response_indicates_cannot_fulfill(
            quote.fulfillment_note or quote.notes,
            request.response_text,
        ):
            _apply_supplier_exclusion(
                project=project,
                outreach=outreach,
                supplier_index=request.supplier_index,
                supplier_name=supplier.name,
                reason=quote.fulfillment_note
                or "Supplier indicated they cannot fulfill this request",
            )
            await record_supplier_interaction(
                project=project,
                supplier_index=request.supplier_index,
                interaction_type="supplier_excluded",
                source="outreach",
                details={
                    "reason": quote.fulfillment_note
                    or "Supplier indicated they cannot fulfill this request",
                },
            )
            await record_project_event(
                project,
                event_type="supplier_excluded",
                title="Supplier removed",
                description=(
                    f"{supplier.name} was removed: "
                    f"{quote.fulfillment_note or 'Cannot fulfill request'}"
                ),
                priority="high",
                phase="outreach",
                payload={"supplier_index": request.supplier_index},
            )

        _append_event(
            outreach,
            "quote_parsed",
            supplier_index=request.supplier_index,
            supplier_name=supplier.name,
            confidence=quote.confidence_score,
        )
        await record_supplier_interaction(
            project=project,
            supplier_index=request.supplier_index,
            interaction_type="quote_parsed",
            source="outreach",
            details={
                "confidence_score": quote.confidence_score,
                "unit_price": quote.unit_price,
                "currency": quote.currency,
                "moq": quote.moq,
                "lead_time": quote.lead_time,
            },
        )
        await record_project_event(
            project,
            event_type="quote_parsed",
            title="Supplier quote parsed",
            description=f"Parsed quote from {supplier.name}.",
            priority="info",
            phase="compare",
            payload={
                "supplier_index": request.supplier_index,
                "confidence_score": quote.confidence_score,
            },
        )

        project["outreach_state"] = outreach.model_dump(mode="json")

        await _save_project(project)

        return quote.model_dump()

    except Exception as e:
        logger.error("Response parsing failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow-up")
async def generate_follow_up_emails(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Generate follow-up emails for non-responsive suppliers."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    reqs = ParsedRequirements(**project["parsed_requirements"])

    try:
        result = await generate_follow_ups(outreach, reqs)

        outreach.follow_up_emails.extend(result.follow_ups)
        _append_event(outreach, "followup_drafted", count=len(result.follow_ups))
        project["outreach_state"] = outreach.model_dump(mode="json")
        await record_project_event(
            project,
            event_type="followups_drafted",
            title="Follow-up drafts ready",
            description=f"Generated {len(result.follow_ups)} follow-up draft(s).",
            priority="info",
            phase="outreach",
            payload={"count": len(result.follow_ups)},
        )
        await _save_project(project)

        return {"follow_ups": [fu.model_dump() for fu in result.follow_ups], "summary": result.summary}

    except Exception as e:
        logger.error("Follow-up generation failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-follow-up/{follow_up_index}")
async def send_follow_up(
    project_id: str,
    follow_up_index: int,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Send an approved follow-up email."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    set_owner_email(outreach, owner_email)

    if follow_up_index < 0 or follow_up_index >= len(outreach.follow_up_emails):
        raise HTTPException(status_code=400, detail="Invalid follow-up index")

    fu = outreach.follow_up_emails[follow_up_index]
    recipient = fu.recipient_email

    if not recipient:
        discovery = DiscoveryResults(**project["discovery_results"])
        if fu.supplier_index < len(discovery.suppliers):
            recipient = discovery.suppliers[fu.supplier_index].email

    if not recipient:
        fu.status = "failed"
        _append_event(outreach, "followup_send_failed", supplier_index=fu.supplier_index, supplier_name=fu.supplier_name, reason="missing_email")
        record_outbound_email(
            outreach,
            supplier_index=fu.supplier_index,
            supplier_name=fu.supplier_name,
            to_email=None,
            from_email=settings.from_email,
            cc_emails=_cc_list(owner_email),
            subject=fu.subject,
            body=fu.body,
            resend_email_id=None,
            delivery_status="failed",
            source="manual_followup",
            event_type="followup_send_failed",
            details={"reason": "missing_email", "follow_up_number": fu.follow_up_number},
        )
        await record_supplier_interaction(
            project=project,
            supplier_index=fu.supplier_index,
            interaction_type="followup_send_failed",
            source="outreach",
            details={"reason": "missing_email"},
        )
        await record_project_event(
            project,
            event_type="followup_send_failed",
            title="Follow-up failed",
            description=f"No email found for {fu.supplier_name}.",
            priority="high",
            phase="outreach",
            payload={"supplier_index": fu.supplier_index},
        )
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)
        return {"sent": False, "error": f"No email for {fu.supplier_name}"}

    result = await _send_and_track_email(
        project=project,
        outreach=outreach,
        supplier_index=fu.supplier_index,
        supplier_name=fu.supplier_name,
        recipient=recipient,
        subject=fu.subject,
        body=fu.body,
        source_label="manual_followup",
        owner_email=owner_email,
    )

    if result.get("sent"):
        fu.status = "sent"
        for status in outreach.supplier_statuses:
            if status.supplier_index == fu.supplier_index:
                status.follow_ups_sent += 1
                status.last_follow_up_at = time.time()
                email_id = result.get("id", "")
                if email_id:
                    status.email_id = email_id
                    if email_id not in status.email_ids:
                        status.email_ids.append(email_id)
                    status.delivery_status = "sent"
                    status.send_error = None
                break
        _append_event(outreach, "followup_sent", supplier_index=fu.supplier_index, supplier_name=fu.supplier_name)
        await record_supplier_interaction(
            project=project,
            supplier_index=fu.supplier_index,
            interaction_type="followup_sent",
            source="outreach",
            details={
                "recipient": recipient,
                "follow_up_number": fu.follow_up_number,
                "cc_owner_email": owner_email,
                "email_id": result.get("id", ""),
            },
        )
        await record_project_event(
            project,
            event_type="followup_sent",
            title="Follow-up sent",
            description=f"Sent follow-up #{fu.follow_up_number} to {fu.supplier_name}.",
            priority="info",
            phase="outreach",
            payload={"supplier_index": fu.supplier_index, "follow_up_number": fu.follow_up_number},
        )
    else:
        fu.status = "failed"
        for status in outreach.supplier_statuses:
            if status.supplier_index == fu.supplier_index:
                _set_supplier_delivery_failure(status, result.get("error", "unknown"))
                break
        _append_event(outreach, "followup_send_failed", supplier_index=fu.supplier_index, supplier_name=fu.supplier_name, reason=result.get("error", "unknown"))
        await record_supplier_interaction(
            project=project,
            supplier_index=fu.supplier_index,
            interaction_type="followup_send_failed",
            source="outreach",
            details={"reason": result.get("error", "unknown"), "recipient": recipient},
        )
        await record_project_event(
            project,
            event_type="followup_send_failed",
            title="Follow-up failed",
            description=(
                f"Follow-up send failed for {fu.supplier_name}: {result.get('error', 'unknown')}"
            ),
            priority="high",
            phase="outreach",
            payload={"supplier_index": fu.supplier_index, "reason": result.get("error", "unknown")},
        )

    project["outreach_state"] = outreach.model_dump(mode="json")

    await _save_project(project)

    return {"sent": result.get("sent", False), "error": result.get("error"), "supplier_name": fu.supplier_name}


@router.get("/status")
async def get_outreach_status(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Get full outreach state for a project."""
    project = await _get_project(project_id, current_user)
    return project.get("outreach_state") or {"error": "No outreach started"}


@router.get("/plan")
async def get_outreach_plan(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Return intent-to-purchase execution plan and funnel metrics."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)

    sent = sum(1 for s in outreach.supplier_statuses if s.email_sent)
    responded = sum(1 for s in outreach.supplier_statuses if s.response_received)
    quoted = len(outreach.parsed_quotes)

    friction = Counter()
    for plan in outreach.supplier_plans:
        friction.update(plan.friction_risks)

    return {
        "selected_suppliers": len(outreach.selected_suppliers),
        "funnel": {
            "intent": len(outreach.selected_suppliers),
            "rfq_sent": sent,
            "responses": responded,
            "quotes_parsed": quoted,
        },
        "friction_risks": dict(friction),
        "plans": [plan.model_dump() for plan in outreach.supplier_plans],
    }


@router.get("/timeline")
async def get_outreach_timeline(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Get immutable timeline events for outreach analytics."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    return {"events": [event.model_dump() for event in outreach.events], "count": len(outreach.events)}


@router.post("/recompare")
async def recompare_with_quotes(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Re-run comparison and recommendation using real quote data."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)

    if not outreach.parsed_quotes:
        raise HTTPException(status_code=400, detail="No parsed quotes to compare")

    try:
        from app.agents.orchestrator import rerun_from_stage

        modified = {}
        active_quotes = [
            q for q in outreach.parsed_quotes if q.supplier_index not in outreach.excluded_suppliers
        ]
        if not active_quotes:
            raise HTTPException(status_code=400, detail="All quoted suppliers are excluded")

        comp = project.get("comparison_result", {})
        comp["_real_quotes"] = [q.model_dump(mode="json") for q in active_quotes]
        modified["comparison_result"] = comp

        state = await rerun_from_stage(project, "compare", modified)

        if state.get("comparison_result"):
            project["comparison_result"] = state["comparison_result"]
        if state.get("recommendation_result"):
            project["recommendation_result"] = state["recommendation_result"]

        for idx in outreach.excluded_suppliers:
            _apply_supplier_exclusion(
                project=project,
                outreach=outreach,
                supplier_index=idx,
                supplier_name="Excluded supplier",
                reason="Excluded from outreach responses",
            )
        project["current_stage"] = "complete"
        project["status"] = "complete"

        _append_event(outreach, "recompare_completed", quote_count=len(outreach.parsed_quotes))
        project["outreach_state"] = outreach.model_dump(mode="json")
        await record_project_event(
            project,
            event_type="recompare_completed",
            title="Comparison refreshed with real quotes",
            description=f"Updated comparison using {len(outreach.parsed_quotes)} parsed quote(s).",
            priority="info",
            phase="compare",
            payload={"quote_count": len(outreach.parsed_quotes)},
        )
        await _save_project(project)

        return {"status": "success", "message": f"Re-compared with {len(outreach.parsed_quotes)} real quotes"}

    except Exception as e:
        logger.error("Recompare failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-send")
async def trigger_auto_send(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Immediately send any queued drafts for this project."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    set_owner_email(outreach, owner_email)

    queued = [d for d in outreach.draft_emails if d.status == "auto_queued"]
    if not queued:
        return {"status": "nothing_to_send", "queued_count": 0}

    discovery = DiscoveryResults(**project["discovery_results"])

    sent = 0
    failed = 0
    for draft in queued:
        status = _get_or_create_supplier_status(
            outreach=outreach,
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
        )

        if status.excluded or draft.supplier_index in outreach.excluded_suppliers:
            draft.status = "failed"
            failed += 1
            _set_supplier_delivery_failure(status, status.exclusion_reason or "Supplier excluded from outreach")
            record_outbound_email(
                outreach,
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                to_email=draft.recipient_email,
                from_email=settings.from_email,
                cc_emails=_cc_list(owner_email),
                subject=draft.subject,
                body=draft.body,
                resend_email_id=None,
                delivery_status="failed",
                source="auto_send_endpoint",
                event_type="send_failed",
                details={"reason": "supplier_excluded"},
            )
            _append_event(
                outreach,
                "send_failed",
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                reason="supplier_excluded",
                source="auto_send_endpoint",
            )
            continue

        recipient = draft.recipient_email
        if not recipient and 0 <= draft.supplier_index < len(discovery.suppliers):
            recipient = discovery.suppliers[draft.supplier_index].email

        if not recipient:
            draft.status = "failed"
            failed += 1
            _set_supplier_delivery_failure(status, "No supplier email found")
            record_outbound_email(
                outreach,
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                to_email=None,
                from_email=settings.from_email,
                cc_emails=_cc_list(owner_email),
                subject=draft.subject,
                body=draft.body,
                resend_email_id=None,
                delivery_status="failed",
                source="auto_send_endpoint",
                event_type="send_failed",
                details={"reason": "missing_email"},
            )
            _append_event(
                outreach,
                "send_failed",
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                reason="missing_email",
                source="auto_send_endpoint",
            )
            continue

        result = await _send_and_track_email(
            project=project,
            outreach=outreach,
            supplier_index=draft.supplier_index,
            supplier_name=draft.supplier_name,
            recipient=recipient,
            subject=draft.subject,
            body=draft.body,
            source_label="auto_send_endpoint",
            owner_email=owner_email,
        )
        if result.get("sent"):
            draft.status = "sent"
            sent += 1
            _set_supplier_delivery_success(status, result.get("id", ""))
            _append_event(
                outreach,
                "email_sent",
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                email_id=result.get("id", ""),
                source="auto_send_endpoint",
            )
        else:
            draft.status = "failed"
            failed += 1
            _set_supplier_delivery_failure(status, result.get("error", "unknown"))
            _append_event(
                outreach,
                "send_failed",
                supplier_index=draft.supplier_index,
                supplier_name=draft.supplier_name,
                reason=result.get("error", "unknown"),
                source="auto_send_endpoint",
            )

    project["outreach_state"] = outreach.model_dump(mode="json")
    await _save_project(project)
    remaining_queued = len([d for d in outreach.draft_emails if d.status == "auto_queued"])
    return {
        "status": "processed",
        "emails_sent": sent,
        "failed_count": failed,
        "remaining_queued": remaining_queued,
    }


@router.get("/scheduler-status")
async def get_scheduler_status(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Return scheduler health, loop counts, and last-run timestamps."""
    await _get_project(project_id, current_user)  # Validate ownership and project

    from app.core.scheduler import get_scheduler
    scheduler = get_scheduler()
    return scheduler.stats


@router.post("/auto-config")
async def set_auto_outreach_config(
    project_id: str,
    config: AutoOutreachConfig,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Save auto-outreach configuration for a project."""
    project = await _get_project(project_id, current_user)

    raw = project.get("outreach_state")
    if raw:
        outreach = OutreachState(**raw) if isinstance(raw, dict) else raw
    else:
        outreach = OutreachState()

    outreach.auto_config = config
    _append_event(outreach, "auto_configured", mode=config.mode, threshold=config.auto_send_threshold)
    project["outreach_state"] = outreach.model_dump(mode="json")
    await _save_project(project)

    return {"status": "saved", "config": config.model_dump()}


@router.post("/auto-start")
async def start_auto_outreach(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Auto-select eligible suppliers and send RFQ emails immediately."""
    project = await _get_project(project_id, current_user)

    if not project.get("recommendation_result"):
        raise HTTPException(status_code=400, detail="Pipeline must complete before auto-outreach")
    if not project.get("verification_results"):
        raise HTTPException(status_code=400, detail="Verification results required for auto-outreach")

    raw = project.get("outreach_state")
    if not raw:
        raise HTTPException(status_code=400, detail="Set auto-config first via /auto-config")

    outreach = OutreachState(**raw) if isinstance(raw, dict) else raw
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    set_owner_email(outreach, owner_email)
    if not outreach.auto_config:
        raise HTTPException(status_code=400, detail="Set auto-config first via /auto-config")

    try:
        reqs = ParsedRequirements(**project["parsed_requirements"])
        discovery = DiscoveryResults(**project["discovery_results"])
        verifications = VerificationResults(**project["verification_results"])
        recs = RecommendationResult(**project["recommendation_result"])

        score_by_index = {
            v.supplier_index: v.composite_score
            for v in verifications.verifications
        }
        threshold = outreach.auto_config.auto_send_threshold
        max_count = outreach.auto_config.max_concurrent_outreach

        selected_indices: list[int] = []
        selected_suppliers: list[DiscoveredSupplier] = []
        for rec in sorted(recs.recommendations, key=lambda r: r.rank):
            idx = rec.supplier_index
            if idx in outreach.excluded_suppliers:
                continue
            if score_by_index.get(idx, 0) < threshold:
                continue
            if not (0 <= idx < len(discovery.suppliers)):
                continue
            selected_indices.append(idx)
            selected_suppliers.append(discovery.suppliers[idx])
            if len(selected_indices) >= max_count:
                break

        if not selected_suppliers:
            return {
                "status": "no_eligible_suppliers",
                "sent_count": 0,
                "failed_count": 0,
                "selected_suppliers": [],
            }

        business_profile = await _fetch_business_profile(current_user.user_id)

        batch_result = await _draft_and_send_initial_outreach(
            project=project,
            outreach=outreach,
            reqs=reqs,
            recs=recs,
            selected_indices=selected_indices,
            selected_suppliers=selected_suppliers,
            source_label="auto_start",
            owner_email=owner_email,
            business_profile=business_profile,
        )

        _append_event(
            outreach,
            "auto_send_completed",
            selected_suppliers=batch_result["selected_count"],
            sent_count=batch_result["sent_count"],
            failed_count=batch_result["failed_count"],
        )
        await record_supplier_interactions(
            project=project,
            supplier_indices=selected_indices,
            interaction_type="auto_outreach_started",
            source="outreach",
            details={
                "selected_count": batch_result["selected_count"],
                "sent_count": batch_result["sent_count"],
                "failed_count": batch_result["failed_count"],
            },
        )
        project["outreach_state"] = outreach.model_dump(mode="json")
        await record_project_event(
            project,
            event_type="auto_outreach_sent",
            title="Auto outreach executed",
            description=(
                f"Auto mode selected {batch_result['selected_count']} supplier(s): "
                f"{batch_result['sent_count']} sent, {batch_result['failed_count']} failed."
            ),
            priority="info",
            phase="outreach",
            payload=batch_result,
        )
        await _save_project(project)

        return {
            "status": "sent",
            "selected_suppliers": selected_indices,
            "sent_count": batch_result["sent_count"],
            "failed_count": batch_result["failed_count"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auto-outreach start failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-status")
async def get_auto_outreach_status(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Get the status of auto-outreach queue for a project."""
    project = await _get_project(project_id, current_user)
    raw = project.get("outreach_state")

    if not raw:
        return {"enabled": False, "message": "No outreach configured"}

    outreach = OutreachState(**raw) if isinstance(raw, dict) else raw

    auto_queued = [d for d in outreach.draft_emails if d.status == "auto_queued"]
    auto_sent = [d for d in outreach.draft_emails if d.status == "sent"]
    auto_failed = [d for d in outreach.draft_emails if d.status == "failed"]

    return {
        "enabled": outreach.auto_config is not None,
        "config": outreach.auto_config.model_dump() if outreach.auto_config else None,
        "queued_count": len(auto_queued),
        "sent_count": len(auto_sent),
        "failed_count": len(auto_failed),
        "queued_suppliers": [d.supplier_name for d in auto_queued],
        "sent_suppliers": [d.supplier_name for d in auto_sent],
        "failed_suppliers": [d.supplier_name for d in auto_failed],
    }


@router.get("/delivery-status")
async def get_delivery_status(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Get email delivery status for all sent emails in this project."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)

    delivery_info = []
    for status in outreach.supplier_statuses:
        if status.email_sent:
            delivery_info.append(
                {
                    "supplier_name": status.supplier_name,
                    "supplier_index": status.supplier_index,
                    "email_id": status.email_id,
                    "delivery_status": status.delivery_status,
                    "sent_at": status.sent_at,
                    "events": [e.model_dump() for e in status.delivery_events],
                }
            )

    return {"total_sent": len(delivery_info), "deliveries": delivery_info}


@router.get("/monitor")
async def get_communication_monitor(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Get full communication monitor state for outreach."""
    project = await _get_project(project_id, current_user)
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    raw = project.get("outreach_state")
    if raw:
        outreach = OutreachState(**raw) if isinstance(raw, dict) else raw
    else:
        # Return an empty monitor snapshot instead of 400 when outreach has not started yet.
        outreach = OutreachState()
    set_owner_email(outreach, owner_email)
    ensure_monitor(outreach, owner_email=owner_email)

    return outreach.communication_monitor.model_dump()


@router.post("/check-inbox")
async def check_inbox(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Check email inbox for supplier responses."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)
    owner_email = _owner_email_from_user(current_user)
    if owner_email:
        project["owner_email"] = owner_email
    else:
        owner_email = await resolve_project_owner_email(project)
    set_owner_email(outreach, owner_email)

    discovery = DiscoveryResults(**project["discovery_results"])
    supplier_emails = []
    supplier_domains = []
    for idx in outreach.selected_suppliers:
        if idx < len(discovery.suppliers):
            supplier = discovery.suppliers[idx]
            if supplier.email:
                supplier_emails.append(supplier.email)
            if supplier.website:
                from urllib.parse import urlparse

                try:
                    domain = urlparse(supplier.website).netloc.replace("www.", "")
                    if domain:
                        supplier_domains.append(domain)
                except Exception:
                    pass

    try:
        from app.agents.inbox_monitor import get_monitor

        monitor = get_monitor("gmail")
        messages = await monitor.check_once(
            config={"supplier_emails": supplier_emails, "supplier_domains": supplier_domains, "max_results": 20},
            project_id=project_id,
        )

        record_inbox_check(
            outreach,
            source="manual_check_inbox",
            message_count=len(messages),
        )

        new_messages = 0
        parsed_count = 0
        parse_failures = 0
        reqs = ParsedRequirements(**project["parsed_requirements"])

        for msg in messages:
            sender = msg.get("sender", "")
            subject = msg.get("subject")
            body = msg.get("body", "")
            snippet = msg.get("snippet")
            inbox_message_id = msg.get("message_id")
            matched = msg.get("matched_supplier")
            supplier_idx, supplier_name = _match_supplier_index_from_token(outreach, discovery, matched)

            _, is_new = record_inbound_email(
                outreach,
                inbox_message_id=inbox_message_id,
                sender=sender,
                subject=subject,
                body=body,
                snippet=snippet,
                matched_sender=matched,
                supplier_index=supplier_idx,
                supplier_name=supplier_name,
                source="manual_check_inbox",
            )
            if is_new:
                new_messages += 1

            if supplier_idx is None or not body or len(body.strip()) < 10:
                continue

            supplier_status = next(
                (s for s in outreach.supplier_statuses if s.supplier_index == supplier_idx),
                None,
            )
            if supplier_status and supplier_status.response_received:
                continue

            try:
                quote = await parse_supplier_response(
                    supplier_name=supplier_name or discovery.suppliers[supplier_idx].name,
                    supplier_index=supplier_idx,
                    response_text=body,
                    requirements=reqs,
                )

                outreach.parsed_quotes.append(quote)
                if supplier_status:
                    supplier_status.response_received = True
                    supplier_status.response_text = body
                    supplier_status.parsed_quote = quote

                mark_inbound_message_parsed(
                    outreach,
                    inbox_message_id=inbox_message_id,
                    supplier_index=supplier_idx,
                    confidence_score=quote.confidence_score,
                    source="manual_check_inbox",
                )
                parsed_count += 1

                if quote.can_fulfill is False or _response_indicates_cannot_fulfill(
                    quote.fulfillment_note or quote.notes,
                    body,
                ):
                    _apply_supplier_exclusion(
                        project=project,
                        outreach=outreach,
                        supplier_index=supplier_idx,
                        supplier_name=supplier_name or discovery.suppliers[supplier_idx].name,
                        reason=quote.fulfillment_note
                        or "Supplier indicated they cannot fulfill this request",
                    )

                _append_event(
                    outreach,
                    "auto_response_parsed",
                    supplier_index=supplier_idx,
                    supplier_name=supplier_name,
                    confidence=quote.confidence_score,
                    source="manual_check_inbox",
                )
            except Exception:
                parse_failures += 1
                logger.warning("Inbox parse failed for project %s message %s", project_id, inbox_message_id, exc_info=True)

        _append_event(outreach, "inbox_checked", messages_found=len(messages))
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)

        return {
            "messages_found": len(messages),
            "new_messages": new_messages,
            "parsed_quotes": parsed_count,
            "parse_failures": parse_failures,
            "messages": messages,
            "searched_emails": supplier_emails,
            "searched_domains": supplier_domains,
            "communication_monitor": outreach.communication_monitor.model_dump(),
        }

    except Exception as e:
        logger.error("Inbox check failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
