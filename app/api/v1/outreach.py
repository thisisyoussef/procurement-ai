"""Outreach API endpoints — manage RFQ emails, responses, and follow-ups."""

import logging
import time
import traceback

from fastapi import APIRouter, HTTPException

from app.agents.followup_agent import generate_follow_ups
from app.agents.outreach_agent import auto_draft_and_queue, draft_outreach_emails
from app.agents.response_parser import parse_supplier_response
from app.core.email_service import send_email
from app.schemas.agent_state import (
    AutoOutreachConfig,
    DiscoveredSupplier,
    DiscoveryResults,
    OutreachState,
    ParsedRequirements,
    RecommendationResult,
    SupplierOutreachStatus,
    VerificationResults,
)
from app.schemas.project import (
    EmailApprovalRequest,
    OutreachStartRequest,
    QuoteParseRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/outreach", tags=["outreach"])


def _get_project(project_id: str) -> dict:
    from app.api.v1.projects import _projects

    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_outreach_state(project: dict) -> OutreachState:
    raw = project.get("outreach_state")
    if not raw:
        raise HTTPException(status_code=400, detail="No outreach started for this project")
    return OutreachState(**raw) if isinstance(raw, dict) else raw


@router.post("/start")
async def start_outreach(project_id: str, request: OutreachStartRequest):
    """Select suppliers and draft personalized RFQ emails."""
    project = _get_project(project_id)

    if not project.get("recommendation_result"):
        raise HTTPException(status_code=400, detail="Pipeline must complete before outreach")

    try:
        reqs = ParsedRequirements(**project["parsed_requirements"])
        discovery = DiscoveryResults(**project["discovery_results"])
        recs = RecommendationResult(**project["recommendation_result"])

        # Get selected suppliers by index
        selected: list[DiscoveredSupplier] = []
        for idx in request.supplier_indices:
            if idx < len(discovery.suppliers):
                selected.append(discovery.suppliers[idx])

        if not selected:
            raise HTTPException(status_code=400, detail="No valid supplier indices provided")

        # Draft emails
        result = await draft_outreach_emails(selected, reqs, recs)

        # Initialize outreach state
        supplier_statuses = [
            SupplierOutreachStatus(
                supplier_name=s.name,
                supplier_index=idx,
            )
            for idx, s in zip(request.supplier_indices, selected)
        ]

        outreach = OutreachState(
            selected_suppliers=request.supplier_indices,
            supplier_statuses=supplier_statuses,
            draft_emails=result.drafts,
        )
        project["outreach_state"] = outreach.model_dump(mode="json")

        return {
            "drafts": [d.model_dump() for d in result.drafts],
            "summary": result.summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Outreach start failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{draft_index}")
async def approve_and_send(project_id: str, draft_index: int, request: EmailApprovalRequest):
    """Approve (optionally edit) and send a draft email."""
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    if draft_index < 0 or draft_index >= len(outreach.draft_emails):
        raise HTTPException(status_code=400, detail="Invalid draft index")

    draft = outreach.draft_emails[draft_index]

    # Apply edits if provided
    if request.edited_subject:
        draft.subject = request.edited_subject
    if request.edited_body:
        draft.body = request.edited_body

    # Determine recipient
    recipient = draft.recipient_email
    if not recipient:
        # Try to find email from discovery results
        discovery = DiscoveryResults(**project["discovery_results"])
        if draft.supplier_index < len(discovery.suppliers):
            recipient = discovery.suppliers[draft.supplier_index].email

    if not recipient:
        draft.status = "failed"
        project["outreach_state"] = outreach.model_dump(mode="json")
        return {
            "sent": False,
            "error": f"No email address found for {draft.supplier_name}. You'll need to provide one.",
        }

    # Send email
    result = await send_email(to=recipient, subject=draft.subject, body_html=draft.body)

    if result.get("sent"):
        draft.status = "sent"
        email_id = result.get("id", "")
        # Update supplier outreach status with email ID for delivery tracking
        for status in outreach.supplier_statuses:
            if status.supplier_index == draft.supplier_index:
                status.email_sent = True
                status.sent_at = time.time()
                status.email_id = email_id
                status.delivery_status = "sent"
                break
    else:
        draft.status = "failed"

    project["outreach_state"] = outreach.model_dump(mode="json")

    return {
        "sent": result.get("sent", False),
        "error": result.get("error"),
        "supplier_name": draft.supplier_name,
    }


@router.post("/parse-response")
async def parse_response(project_id: str, request: QuoteParseRequest):
    """Parse a pasted supplier response into structured quote data."""
    project = _get_project(project_id)
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

        # Store the parsed quote
        outreach.parsed_quotes.append(quote)

        # Update supplier status
        for status in outreach.supplier_statuses:
            if status.supplier_index == request.supplier_index:
                status.response_received = True
                status.response_text = request.response_text
                status.parsed_quote = quote
                break

        project["outreach_state"] = outreach.model_dump(mode="json")

        return quote.model_dump()

    except Exception as e:
        logger.error("Response parsing failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow-up")
async def generate_follow_up_emails(project_id: str):
    """Generate follow-up emails for non-responsive suppliers."""
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)
    reqs = ParsedRequirements(**project["parsed_requirements"])

    try:
        result = await generate_follow_ups(outreach, reqs)

        # Store follow-up drafts
        outreach.follow_up_emails.extend(result.follow_ups)
        project["outreach_state"] = outreach.model_dump(mode="json")

        return {
            "follow_ups": [fu.model_dump() for fu in result.follow_ups],
            "summary": result.summary,
        }

    except Exception as e:
        logger.error("Follow-up generation failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-follow-up/{follow_up_index}")
async def send_follow_up(project_id: str, follow_up_index: int):
    """Send an approved follow-up email."""
    project = _get_project(project_id)
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
        project["outreach_state"] = outreach.model_dump(mode="json")
        return {"sent": False, "error": f"No email for {fu.supplier_name}"}

    result = await send_email(to=recipient, subject=fu.subject, body_html=fu.body)

    if result.get("sent"):
        fu.status = "sent"
        for status in outreach.supplier_statuses:
            if status.supplier_index == fu.supplier_index:
                status.follow_ups_sent += 1
                status.last_follow_up_at = time.time()
                break
    else:
        fu.status = "failed"

    project["outreach_state"] = outreach.model_dump(mode="json")

    return {
        "sent": result.get("sent", False),
        "error": result.get("error"),
        "supplier_name": fu.supplier_name,
    }


@router.get("/status")
async def get_outreach_status(project_id: str):
    """Get full outreach state for a project."""
    project = _get_project(project_id)
    return project.get("outreach_state") or {"error": "No outreach started"}


@router.post("/recompare")
async def recompare_with_quotes(project_id: str):
    """Re-run comparison and recommendation using real quote data."""
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    if not outreach.parsed_quotes:
        raise HTTPException(status_code=400, detail="No parsed quotes to compare")

    try:
        from app.agents.orchestrator import rerun_from_stage

        # Inject real quote data into comparison context
        modified = {}
        comp = project.get("comparison_result", {})
        comp["_real_quotes"] = [q.model_dump(mode="json") for q in outreach.parsed_quotes]
        modified["comparison_result"] = comp

        state = await rerun_from_stage(project, "compare", modified)

        # Update project with new results
        if state.get("comparison_result"):
            project["comparison_result"] = state["comparison_result"]
        if state.get("recommendation_result"):
            project["recommendation_result"] = state["recommendation_result"]
        project["current_stage"] = "complete"
        project["status"] = "complete"

        return {
            "status": "success",
            "message": f"Re-compared with {len(outreach.parsed_quotes)} real quotes",
        }

    except Exception as e:
        logger.error("Recompare failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ── Auto-Outreach Endpoints ─────────────────────────────────────


@router.post("/auto-config")
async def set_auto_outreach_config(project_id: str, config: AutoOutreachConfig):
    """Save auto-outreach configuration for a project."""
    project = _get_project(project_id)

    # Get or create outreach state
    raw = project.get("outreach_state")
    if raw:
        outreach = OutreachState(**raw) if isinstance(raw, dict) else raw
    else:
        outreach = OutreachState()

    outreach.auto_config = config
    project["outreach_state"] = outreach.model_dump(mode="json")

    return {
        "status": "saved",
        "config": config.model_dump(),
    }


@router.post("/auto-start")
async def start_auto_outreach(project_id: str):
    """Auto-draft and queue RFQ emails for suppliers above the verification threshold.

    Requires:
    - Pipeline must be complete (recommendation_result exists)
    - Auto-config must be set (via /auto-config endpoint)
    - Verification results must exist
    """
    project = _get_project(project_id)

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

        # Merge auto-queued drafts into outreach state
        outreach.draft_emails.extend(result.drafts)

        # Add supplier statuses for auto-queued suppliers
        existing_indices = {s.supplier_index for s in outreach.supplier_statuses}
        for draft in result.drafts:
            if draft.supplier_index not in existing_indices:
                outreach.supplier_statuses.append(
                    SupplierOutreachStatus(
                        supplier_name=draft.supplier_name,
                        supplier_index=draft.supplier_index,
                    )
                )

        project["outreach_state"] = outreach.model_dump(mode="json")

        return {
            "status": "queued",
            "drafts_queued": len(result.drafts),
            "summary": result.summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auto-outreach start failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-status")
async def get_auto_outreach_status(project_id: str):
    """Get the status of auto-outreach queue for a project."""
    project = _get_project(project_id)
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


# ── Delivery Tracking & Inbox Monitoring ──────────────────────────


@router.get("/delivery-status")
async def get_delivery_status(project_id: str):
    """Get email delivery status for all sent emails in this project.

    Returns delivery tracking info from Resend webhooks for each supplier.
    """
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    delivery_info = []
    for status in outreach.supplier_statuses:
        if status.email_sent:
            delivery_info.append({
                "supplier_name": status.supplier_name,
                "supplier_index": status.supplier_index,
                "email_id": status.email_id,
                "delivery_status": status.delivery_status,
                "sent_at": status.sent_at,
                "events": [e.model_dump() for e in status.delivery_events],
            })

    return {
        "total_sent": len(delivery_info),
        "deliveries": delivery_info,
    }


@router.post("/check-inbox")
async def check_inbox(project_id: str):
    """Check email inbox for supplier responses.

    Triggers a one-shot check using the configured inbox monitor (Gmail).
    Returns raw messages that match RFQ response patterns.
    """
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    # Collect known supplier emails and domains
    discovery = DiscoveryResults(**project["discovery_results"])
    supplier_emails = []
    supplier_domains = []
    for idx in outreach.selected_suppliers:
        if idx < len(discovery.suppliers):
            supplier = discovery.suppliers[idx]
            if supplier.email:
                supplier_emails.append(supplier.email)
            if supplier.website:
                # Extract domain from website URL
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
            config={
                "supplier_emails": supplier_emails,
                "supplier_domains": supplier_domains,
                "max_results": 20,
            },
            project_id=project_id,
        )

        return {
            "messages_found": len(messages),
            "messages": messages,
            "searched_emails": supplier_emails,
            "searched_domains": supplier_domains,
        }

    except Exception as e:
        logger.error("Inbox check failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
