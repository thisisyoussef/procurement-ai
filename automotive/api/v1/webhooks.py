"""Webhook endpoints for automotive — handles Resend email events."""

import logging
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks", tags=["automotive-webhooks"])

logger = logging.getLogger(__name__)


@router.post("/email")
async def handle_email_webhook(request: Request) -> dict[str, Any]:
    """Handle inbound email events from Resend.

    Events: email.received, email.delivered, email.bounced, email.opened
    """
    payload = await request.json()
    event_type = payload.get("type", "")

    logger.info("Received email webhook: %s", event_type)

    if event_type == "email.received":
        # Supplier responded to an RFQ
        # TODO: Extract project_id from email thread, trigger quote parsing
        logger.info("Inbound email received from: %s", payload.get("data", {}).get("from"))

    elif event_type == "email.delivered":
        logger.info("Email delivered to: %s", payload.get("data", {}).get("to"))

    elif event_type == "email.bounced":
        logger.warning("Email bounced for: %s", payload.get("data", {}).get("to"))

    elif event_type == "email.opened":
        logger.info("Email opened by: %s", payload.get("data", {}).get("to"))

    return {"status": "ok"}
