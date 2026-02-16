"""Webhook endpoints for automotive — handles Resend email events."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request

from automotive.api.v1.events import emit_activity
from automotive.services.project_service import _in_memory_projects, _persist_state

router = APIRouter(prefix="/webhooks", tags=["automotive-webhooks"])

logger = logging.getLogger(__name__)


def _find_project_and_supplier_by_email_id(
    email_id: str,
) -> tuple[str | None, str | None, dict | None]:
    """Search in-memory projects for a supplier with the given qualification email ID.

    Returns (project_id, supplier_id, qualification_result_dict) or (None, None, None).
    """
    for pid, proj in _in_memory_projects.items():
        qual = proj.get("qualification_result")
        if not qual or not isinstance(qual, dict):
            continue
        for supplier in qual.get("suppliers", []):
            if supplier.get("qualification_email_id") == email_id:
                return pid, supplier.get("supplier_id"), qual
    return None, None, None


@router.post("/email")
async def handle_email_webhook(request: Request) -> dict[str, Any]:
    """Handle inbound email events from Resend.

    Events: email.received, email.delivered, email.bounced, email.opened
    """
    payload = await request.json()
    event_type = payload.get("type", "")
    data = payload.get("data", {})

    logger.info("Received email webhook: %s", event_type)

    # Try to extract the Resend email ID from the event payload
    email_id = data.get("email_id") or data.get("id") or ""

    if not email_id:
        logger.debug("No email_id in webhook payload, skipping supplier lookup")
        return {"status": "ok"}

    # Look up the project and supplier this email belongs to
    project_id, supplier_id, qual_data = _find_project_and_supplier_by_email_id(email_id)

    if not project_id or not qual_data:
        logger.debug("Email %s not matched to any qualification outreach", email_id)
        return {"status": "ok"}

    now_iso = datetime.now(timezone.utc).isoformat()
    updated = False

    # Find and update the supplier in the qualification result
    for supplier in qual_data.get("suppliers", []):
        if supplier.get("supplier_id") != supplier_id:
            continue

        company = supplier.get("company_name", "Unknown")

        if event_type == "email.delivered":
            if supplier.get("qualification_email_status") in ("sent",):
                supplier["qualification_email_status"] = "delivered"
                supplier.setdefault("qualification_events", []).append({
                    "timestamp": now_iso,
                    "event": "email_delivered",
                    "detail": f"Questionnaire delivered to {data.get('to', [''])[0] if isinstance(data.get('to'), list) else data.get('to', '')}",
                })
                emit_activity("qualify", "start", f"Email delivered to {company}", project_id=project_id)
                updated = True

        elif event_type == "email.opened":
            if supplier.get("qualification_email_status") in ("sent", "delivered"):
                supplier["qualification_email_status"] = "opened"
                supplier.setdefault("qualification_events", []).append({
                    "timestamp": now_iso,
                    "event": "email_opened",
                    "detail": f"Questionnaire opened by {company}",
                })
                emit_activity("qualify", "start", f"Email opened by {company}", project_id=project_id)
                updated = True

        elif event_type == "email.bounced":
            supplier["qualification_email_status"] = "bounced"
            supplier.setdefault("qualification_events", []).append({
                "timestamp": now_iso,
                "event": "email_bounced",
                "detail": f"Email bounced: {data.get('bounce_type', 'unknown')}",
            })
            emit_activity("qualify", "error", f"Email to {company} bounced", project_id=project_id)
            updated = True

        elif event_type == "email.received":
            # Inbound reply — log for now, full parsing requires manual trigger or inbox monitor
            supplier.setdefault("qualification_events", []).append({
                "timestamp": now_iso,
                "event": "reply_received",
                "detail": f"Reply received from {data.get('from', 'unknown')}",
            })
            emit_activity("qualify", "complete", f"Reply received from {company}!", project_id=project_id)
            updated = True

        break

    if updated:
        await _persist_state(project_id, {"qualification_result": qual_data})
        logger.info("Updated qualification email status for supplier %s (event: %s)", supplier_id, event_type)

    return {"status": "ok"}
