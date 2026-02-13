"""Outreach API endpoints — manage RFQ emails, responses, and follow-ups."""

import logging
import time
import traceback
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from app.agents.followup_agent import generate_follow_ups
from app.agents.outreach_agent import auto_draft_and_queue, draft_outreach_emails
from app.agents.response_parser import parse_supplier_response
from app.core.email_service import send_email
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
from app.schemas.project import EmailApprovalRequest, OutreachStartRequest, QuoteParseRequest
from app.core.auth import AuthUser, get_current_auth_user
from app.services.project_store import StoreUnavailableError, get_project_store
from app.services.supplier_memory import (
    record_supplier_interaction,
    record_supplier_interactions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/outreach", tags=["outreach"])


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

        result = await draft_outreach_emails(selected, reqs, recs)

        supplier_statuses = [SupplierOutreachStatus(supplier_name=s.name, supplier_index=idx) for idx, s in zip(selected_indices, selected)]

        outreach = OutreachState(
            selected_suppliers=selected_indices,
            supplier_statuses=supplier_statuses,
            draft_emails=result.drafts,
        )

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

        await _save_project(project)
        return {"drafts": [d.model_dump() for d in result.drafts], "summary": result.summary}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Outreach start failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


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

    if draft_index < 0 or draft_index >= len(outreach.draft_emails):
        raise HTTPException(status_code=400, detail="Invalid draft index")

    draft = outreach.draft_emails[draft_index]

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
        _append_event(outreach, "send_failed", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, reason="missing_email")
        await record_supplier_interaction(
            project=project,
            supplier_index=draft.supplier_index,
            interaction_type="rfq_send_failed",
            source="outreach",
            details={"reason": "missing_email"},
        )
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)
        return {"sent": False, "error": f"No email address found for {draft.supplier_name}. You'll need to provide one."}

    _append_event(outreach, "send_attempted", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, recipient=recipient)
    result = await send_email(to=recipient, subject=draft.subject, body_html=draft.body)

    if result.get("sent"):
        draft.status = "sent"
        email_id = result.get("id", "")
        for status in outreach.supplier_statuses:
            if status.supplier_index == draft.supplier_index:
                status.email_sent = True
                status.sent_at = time.time()
                status.email_id = email_id
                status.delivery_status = "sent"
                break
        _append_event(outreach, "email_sent", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, email_id=email_id)
        await record_supplier_interaction(
            project=project,
            supplier_index=draft.supplier_index,
            interaction_type="rfq_sent",
            source="outreach",
            details={"email_id": email_id, "recipient": recipient},
        )
    else:
        draft.status = "failed"
        _append_event(outreach, "send_failed", supplier_index=draft.supplier_index, supplier_name=draft.supplier_name, reason=result.get("error", "unknown"))
        await record_supplier_interaction(
            project=project,
            supplier_index=draft.supplier_index,
            interaction_type="rfq_send_failed",
            source="outreach",
            details={"reason": result.get("error", "unknown"), "recipient": recipient},
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
        await record_supplier_interaction(
            project=project,
            supplier_index=fu.supplier_index,
            interaction_type="followup_send_failed",
            source="outreach",
            details={"reason": "missing_email"},
        )
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)
        return {"sent": False, "error": f"No email for {fu.supplier_name}"}

    result = await send_email(to=recipient, subject=fu.subject, body_html=fu.body)

    if result.get("sent"):
        fu.status = "sent"
        for status in outreach.supplier_statuses:
            if status.supplier_index == fu.supplier_index:
                status.follow_ups_sent += 1
                status.last_follow_up_at = time.time()
                break
        _append_event(outreach, "followup_sent", supplier_index=fu.supplier_index, supplier_name=fu.supplier_name)
        await record_supplier_interaction(
            project=project,
            supplier_index=fu.supplier_index,
            interaction_type="followup_sent",
            source="outreach",
            details={"recipient": recipient, "follow_up_number": fu.follow_up_number},
        )
    else:
        fu.status = "failed"
        _append_event(outreach, "followup_send_failed", supplier_index=fu.supplier_index, supplier_name=fu.supplier_name, reason=result.get("error", "unknown"))
        await record_supplier_interaction(
            project=project,
            supplier_index=fu.supplier_index,
            interaction_type="followup_send_failed",
            source="outreach",
            details={"reason": result.get("error", "unknown"), "recipient": recipient},
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
        comp = project.get("comparison_result", {})
        comp["_real_quotes"] = [q.model_dump(mode="json") for q in outreach.parsed_quotes]
        modified["comparison_result"] = comp

        state = await rerun_from_stage(project, "compare", modified)

        if state.get("comparison_result"):
            project["comparison_result"] = state["comparison_result"]
        if state.get("recommendation_result"):
            project["recommendation_result"] = state["recommendation_result"]
        project["current_stage"] = "complete"
        project["status"] = "complete"

        _append_event(outreach, "recompare_completed", quote_count=len(outreach.parsed_quotes))
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)

        return {"status": "success", "message": f"Re-compared with {len(outreach.parsed_quotes)} real quotes"}

    except Exception as e:
        logger.error("Recompare failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-send")
async def trigger_auto_send(project_id: str):
    """Immediately process the auto-queue for this project (bypass scheduler wait)."""
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    queued = [d for d in outreach.draft_emails if d.status == "auto_queued"]
    if not queued:
        return {"status": "nothing_to_send", "queued_count": 0}

    from app.core.scheduler import get_scheduler
    scheduler = get_scheduler()
    result = await scheduler.process_project_now(project_id)
    return {"status": "processed", **result}


@router.get("/scheduler-status")
async def get_scheduler_status(project_id: str):
    """Return scheduler health, loop counts, and last-run timestamps."""
    _get_project(project_id)  # Validate project exists

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
    """Auto-draft and queue RFQ emails for suppliers above the verification threshold."""
    project = await _get_project(project_id, current_user)

    if not project.get("recommendation_result"):
        raise HTTPException(status_code=400, detail="Pipeline must complete before auto-outreach")
    if not project.get("verification_results"):
        raise HTTPException(status_code=400, detail="Verification results required for auto-outreach")

    raw = project.get("outreach_state")
    if not raw:
        raise HTTPException(status_code=400, detail="Set auto-config first via /auto-config")

    outreach = OutreachState(**raw) if isinstance(raw, dict) else raw
    if not outreach.auto_config:
        raise HTTPException(status_code=400, detail="Set auto-config first via /auto-config")

    try:
        reqs = ParsedRequirements(**project["parsed_requirements"])
        discovery = DiscoveryResults(**project["discovery_results"])
        verifications = VerificationResults(**project["verification_results"])
        recs = RecommendationResult(**project["recommendation_result"])

        result = await auto_draft_and_queue(
            verified_suppliers=discovery.suppliers,
            verifications=verifications,
            requirements=reqs,
            recommendations=recs,
            auto_config=outreach.auto_config,
        )

        outreach.draft_emails.extend(result.drafts)

        existing_indices = {s.supplier_index for s in outreach.supplier_statuses}
        for draft in result.drafts:
            if draft.supplier_index not in existing_indices:
                outreach.supplier_statuses.append(
                    SupplierOutreachStatus(supplier_name=draft.supplier_name, supplier_index=draft.supplier_index)
                )
            if draft.supplier_index not in outreach.selected_suppliers:
                outreach.selected_suppliers.append(draft.supplier_index)

            if 0 <= draft.supplier_index < len(discovery.suppliers):
                plan = _build_supplier_plan(discovery.suppliers[draft.supplier_index], draft.supplier_index, reqs, None)
                _upsert_plan(outreach, plan)

        _append_event(outreach, "auto_queue_created", queued=len(result.drafts))
        await record_supplier_interactions(
            project=project,
            supplier_indices=[d.supplier_index for d in result.drafts],
            interaction_type="auto_outreach_queued",
            source="outreach",
            details={"queued_count": len(result.drafts)},
        )
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)

        return {"status": "queued", "drafts_queued": len(result.drafts), "summary": result.summary}

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

    return {
        "enabled": outreach.auto_config is not None,
        "config": outreach.auto_config.model_dump() if outreach.auto_config else None,
        "queued_count": len(auto_queued),
        "sent_count": len(auto_sent),
        "queued_suppliers": [d.supplier_name for d in auto_queued],
        "sent_suppliers": [d.supplier_name for d in auto_sent],
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


@router.post("/check-inbox")
async def check_inbox(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Check email inbox for supplier responses."""
    project = await _get_project(project_id, current_user)
    outreach = _get_outreach_state(project)

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

        _append_event(outreach, "inbox_checked", messages_found=len(messages))
        project["outreach_state"] = outreach.model_dump(mode="json")
        await _save_project(project)

        return {
            "messages_found": len(messages),
            "messages": messages,
            "searched_emails": supplier_emails,
            "searched_domains": supplier_domains,
        }

    except Exception as e:
        logger.error("Inbox check failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
