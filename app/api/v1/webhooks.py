"""Webhook handlers for Resend (email delivery) and Retell (phone calls)."""

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings
from app.core.email_service import verify_webhook_signature
from app.schemas.agent_state import EmailDeliveryEvent, OutreachState
from app.services.project_store import StoreUnavailableError, get_project_store
from app.services.supplier_memory import record_supplier_interaction

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["webhooks"])


async def _find_project_by_email_id(email_id: str) -> tuple[dict | None, int | None]:
    """Find a project and supplier index by Resend email ID."""
    store = get_project_store()
    try:
        return await store.find_project_by_email_id(email_id)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


async def _find_project_by_call_id(call_id: str) -> tuple[dict | None, int | None]:
    """Find a project and call index by Retell call ID."""
    store = get_project_store()
    try:
        return await store.find_project_by_call_id(call_id)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


async def _save_project(project: dict) -> None:
    store = get_project_store()
    try:
        await store.save_project(project)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


@router.post("/resend")
async def resend_webhook(request: Request):
    """Handle Resend delivery webhooks."""
    body = await request.body()

    if settings.resend_webhook_secret:
        signature = request.headers.get("svix-signature", "")
        if not verify_webhook_signature(body, signature, settings.resend_webhook_secret):
            logger.warning("Invalid Resend webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    event_type = payload.get("type", "")
    data = payload.get("data", {})
    email_id = data.get("email_id") or data.get("id", "")

    if not email_id:
        logger.debug("Resend webhook without email_id: %s", event_type)
        return {"received": True, "matched": False}

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

    project, supplier_index = await _find_project_by_email_id(email_id)

    if not project:
        logger.debug("Resend webhook for unknown email_id: %s", email_id)
        return {"received": True, "matched": False}

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
    if supplier_index is not None:
        await record_supplier_interaction(
            project=project,
            supplier_index=supplier_index,
            interaction_type="email_delivery_update",
            source="webhook_resend",
            details={"event_type": event_type, "delivery_status": delivery_status, "email_id": email_id},
        )
    await _save_project(project)

    logger.info(
        "Resend webhook: %s for email %s (supplier_index=%s)",
        event_type,
        email_id,
        supplier_index,
    )

    return {"received": True, "matched": True, "event": event_type}


@router.post("/retell")
async def retell_webhook(request: Request):
    """Handle Retell AI call status webhooks."""
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    event_type = payload.get("event", "")
    call_data = payload.get("call", payload.get("data", {}))
    call_id = call_data.get("call_id", "")

    if not call_id:
        logger.debug("Retell webhook without call_id: %s", event_type)
        return {"received": True, "matched": False}

    project, call_index = await _find_project_by_call_id(call_id)

    if not project or call_index is None:
        logger.debug("Retell webhook for unknown call_id: %s", call_id)
        return {"received": True, "matched": False}

    raw = project.get("outreach_state", {})
    outreach = OutreachState(**raw) if isinstance(raw, dict) else raw

    if call_index < len(outreach.phone_calls):
        call = outreach.phone_calls[call_index]

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

        for status in outreach.supplier_statuses:
            if status.phone_call_id == call_id:
                status.phone_status = call.status
                if call.transcript:
                    status.phone_transcript = call.transcript
                break

    project["outreach_state"] = outreach.model_dump(mode="json")
    supplier_index = None
    if call_index < len(outreach.phone_calls):
        supplier_index = outreach.phone_calls[call_index].supplier_index
    if isinstance(supplier_index, int):
        await record_supplier_interaction(
            project=project,
            supplier_index=supplier_index,
            interaction_type="phone_call_status_update",
            source="webhook_retell",
            details={"event_type": event_type, "call_id": call_id},
        )
    await _save_project(project)

    logger.info("Retell webhook: %s for call %s", event_type, call_id)

    return {"received": True, "matched": True, "event": event_type}
