"""Webhook handlers for Resend (email delivery) and Retell (phone calls)."""

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings
from app.core.email_service import verify_webhook_signature
from app.schemas.agent_state import EmailDeliveryEvent, OutreachState

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["webhooks"])


def _find_project_by_email_id(email_id: str) -> tuple[dict | None, int | None]:
    """Find a project and supplier index by Resend email ID."""
    from app.api.v1.projects import _projects

    for project in _projects.values():
        raw = project.get("outreach_state")
        if not raw:
            continue
        outreach = raw if isinstance(raw, dict) else raw.model_dump(mode="json")
        for status in outreach.get("supplier_statuses", []):
            if status.get("email_id") == email_id:
                return project, status.get("supplier_index")
    return None, None


def _find_project_by_call_id(call_id: str) -> tuple[dict | None, int | None]:
    """Find a project and call index by Retell call ID."""
    from app.api.v1.projects import _projects

    for project in _projects.values():
        raw = project.get("outreach_state")
        if not raw:
            continue
        outreach = raw if isinstance(raw, dict) else raw.model_dump(mode="json")
        for i, call in enumerate(outreach.get("phone_calls", [])):
            if call.get("call_id") == call_id:
                return project, i
    return None, None


@router.post("/resend")
async def resend_webhook(request: Request):
    """Handle Resend delivery webhooks.

    Resend sends events for: email.sent, email.delivered, email.bounced,
    email.opened, email.clicked, email.complained, email.delivery_delayed.

    The webhook updates the corresponding supplier's delivery status
    in the project's outreach state.
    """
    body = await request.body()

    # Verify signature if secret is configured
    if settings.resend_webhook_secret:
        signature = request.headers.get("svix-signature", "")
        if not verify_webhook_signature(body, signature, settings.resend_webhook_secret):
            logger.warning("Invalid Resend webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type", "")
    data = payload.get("data", {})
    email_id = data.get("email_id") or data.get("id", "")

    if not email_id:
        logger.debug("Resend webhook without email_id: %s", event_type)
        return {"received": True, "matched": False}

    # Map event type to delivery status
    status_map = {
        "email.sent": "sent",
        "email.delivered": "delivered",
        "email.bounced": "bounced",
        "email.opened": "opened",
        "email.clicked": "clicked",
        "email.complained": "complained",
        "email.delivery_delayed": "delayed",
    }

    delivery_status = status_map.get(event_type, event_type)

    # Find the project + supplier this email belongs to
    project, supplier_index = _find_project_by_email_id(email_id)

    if not project:
        logger.debug("Resend webhook for unknown email_id: %s", email_id)
        return {"received": True, "matched": False}

    # Update the outreach state
    raw = project.get("outreach_state", {})
    outreach = OutreachState(**raw) if isinstance(raw, dict) else raw

    for status in outreach.supplier_statuses:
        if status.email_id == email_id:
            status.delivery_status = delivery_status
            status.delivery_events.append(
                EmailDeliveryEvent(
                    event_type=event_type,
                    timestamp=data.get("created_at", str(time.time())),
                    details=data,
                )
            )
            break

    project["outreach_state"] = outreach.model_dump(mode="json")

    logger.info(
        "Resend webhook: %s for email %s (supplier_index=%s)",
        event_type, email_id, supplier_index,
    )

    return {"received": True, "matched": True, "event": event_type}


@router.post("/retell")
async def retell_webhook(request: Request):
    """Handle Retell AI call status webhooks.

    Retell sends events when calls start, end, or fail.
    Updates the corresponding PhoneCallStatus in the project's outreach state.
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("event", "")
    call_data = payload.get("call", payload.get("data", {}))
    call_id = call_data.get("call_id", "")

    if not call_id:
        logger.debug("Retell webhook without call_id: %s", event_type)
        return {"received": True, "matched": False}

    # Find the project this call belongs to
    project, call_index = _find_project_by_call_id(call_id)

    if not project or call_index is None:
        logger.debug("Retell webhook for unknown call_id: %s", call_id)
        return {"received": True, "matched": False}

    # Update the call status
    raw = project.get("outreach_state", {})
    outreach = OutreachState(**raw) if isinstance(raw, dict) else raw

    if call_index < len(outreach.phone_calls):
        call = outreach.phone_calls[call_index]

        # Map Retell events to our status
        if event_type in ("call_started", "call_connected"):
            call.status = "in_progress"
            call.started_at = call_data.get("start_timestamp", str(time.time()))
        elif event_type in ("call_ended", "call_analyzed"):
            call.status = "completed"
            call.ended_at = call_data.get("end_timestamp", str(time.time()))
            call.duration_seconds = call_data.get("duration_ms", 0) / 1000.0
            call.transcript = call_data.get("transcript", "")
            call.recording_url = call_data.get("recording_url")
        elif event_type in ("call_failed", "call_error"):
            call.status = "failed"
            call.ended_at = str(time.time())

        # Also update supplier outreach status if linked
        for status in outreach.supplier_statuses:
            if status.phone_call_id == call_id:
                status.phone_status = call.status
                if call.transcript:
                    status.phone_transcript = call.transcript
                break

    project["outreach_state"] = outreach.model_dump(mode="json")

    logger.info("Retell webhook: %s for call %s", event_type, call_id)

    return {"received": True, "matched": True, "event": event_type}
