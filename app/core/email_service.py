"""Email service — Resend SDK wrapper with webhook verification and HTML templates."""

import asyncio
import base64
import binascii
import hashlib
import hmac
import logging
import time
from collections import deque
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _extract_resend_email_id(result: Any) -> str:
    """Extract an email ID from common Resend SDK response shapes."""
    if isinstance(result, dict):
        email_id = result.get("id")
        if email_id:
            return str(email_id)
        data = result.get("data")
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        return ""
    email_id = getattr(result, "id", None)
    if email_id:
        return str(email_id)
    data = getattr(result, "data", None)
    if isinstance(data, dict) and data.get("id"):
        return str(data["id"])
    return ""


def _send_with_resend(api_key: str, payload: dict[str, Any]) -> Any:
    import resend

    resend.api_key = api_key
    return resend.Emails.send(payload)


async def send_email(
    to: str,
    subject: str,
    body_html: str,
    *,
    cc: list[str] | None = None,
    reply_to: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    """Send an email via Resend API.

    Returns the Resend response dict with 'id' and 'sent' keys.
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.warning("Resend API key not configured — email not sent to %s", to)
        return {"error": "Resend API key not configured", "sent": False}
    from_email = (settings.from_email or "").strip() or "sourcing@asmbl.app"
    if from_email == "sourcing@yourdomain.com":
        logger.warning("FROM_EMAIL is still placeholder value; refusing to send to %s", to)
        return {
            "error": "FROM_EMAIL is not configured (still sourcing@yourdomain.com)",
            "sent": False,
        }

    try:
        normalized_cc = []
        seen: set[str] = set()
        for candidate in cc or []:
            value = (candidate or "").strip().lower()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_cc.append(value)

        payload = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "html": body_html,
        }
        if normalized_cc:
            payload["cc"] = normalized_cc
        if reply_to:
            payload["reply_to"] = reply_to
        if headers:
            payload["headers"] = headers

        result = await asyncio.to_thread(_send_with_resend, settings.resend_api_key, payload)
        email_id = _extract_resend_email_id(result)
        if not email_id:
            logger.error("Resend returned no email id for %s: %r", to, result)
            return {"error": "Resend response missing email id", "sent": False}
        logger.info(
            "Email sent to %s (cc=%s): subject=%s, id=%s",
            to,
            ",".join(normalized_cc) if normalized_cc else "-",
            subject[:60],
            email_id,
        )
        return {
            "id": email_id,
            "sent": True,
            "to": to,
            "cc": normalized_cc,
            "from": from_email,
        }

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, str(e))
        return {"error": str(e), "sent": False}


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    *,
    svix_id: str | None = None,
    svix_timestamp: str | None = None,
) -> bool:
    """Verify a Resend webhook signature using HMAC-SHA256.

    Args:
        payload: Raw request body bytes
        signature: The signature from the 'svix-signature' header
        secret: The webhook signing secret from Resend dashboard

    Returns:
        True if signature is valid
    """
    if not secret or not signature:
        return False

    try:
        normalized_secret = secret.strip()
        if normalized_secret.startswith("whsec_"):
            normalized_secret = normalized_secret[6:]

        try:
            secret_bytes = base64.b64decode(normalized_secret)
        except (binascii.Error, ValueError):
            # Fallback for non-base64 legacy secrets.
            secret_bytes = secret.encode("utf-8")

        # Preferred Svix verification path:
        #   signed_content = "{svix-id}.{svix-timestamp}.{payload}"
        #   signature header contains one or more "v1,<base64sig>" entries.
        if svix_id and svix_timestamp:
            signed_content = (
                f"{svix_id}.{svix_timestamp}.{payload.decode('utf-8')}".encode("utf-8")
            )
            digest = hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
            expected_b64 = base64.b64encode(digest).decode("utf-8")

            candidates: list[str] = []
            for part in signature.split():
                token = part.strip()
                if not token:
                    continue
                if "," in token:
                    version, value = token.split(",", 1)
                    if version == "v1":
                        candidates.append(value)
                else:
                    candidates.append(token)

            if any(hmac.compare_digest(expected_b64, candidate) for candidate in candidates):
                return True

        # Backward-compatible fallback for local/dev signatures.
        expected_legacy = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected_legacy, signature):
            return True
        if signature.startswith("v1,"):
            _, maybe_sig = signature.split(",", 1)
            if hmac.compare_digest(expected_legacy, maybe_sig):
                return True
        return False
    except Exception as e:
        logger.warning("Webhook signature verification failed: %s", e)
        return False


def build_rfq_html(
    supplier_name: str,
    company_name: str,
    body: str,
    requirements_summary: str | None = None,
) -> str:
    """Build a branded HTML email template for RFQ outreach.

    Args:
        supplier_name: Name of the supplier being contacted
        company_name: Name of the buying company
        body: The email body content (can contain HTML)
        requirements_summary: Optional requirements summary block

    Returns:
        Full HTML email string with inline CSS
    """
    requirements_block = ""
    if requirements_summary:
        requirements_block = f"""
        <div style="background-color: #f8f9fa; border-left: 4px solid #4a90d9;
                    padding: 16px; margin: 20px 0; border-radius: 4px;">
            <h3 style="margin: 0 0 8px 0; color: #333; font-size: 14px;">
                Requirements Summary
            </h3>
            <p style="margin: 0; color: #555; font-size: 13px; white-space: pre-line;">
                {requirements_summary}
            </p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont,
                 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #ffffff; border-radius: 8px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden;">
                <!-- Header -->
                <div style="background-color: #1a365d; padding: 24px 32px;">
                    <h1 style="margin: 0; color: #ffffff; font-size: 18px; font-weight: 600;">
                        {company_name}
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #a0bce0; font-size: 13px;">
                        Request for Quotation
                    </p>
                </div>

                <!-- Body -->
                <div style="padding: 32px;">
                    <p style="color: #333; font-size: 14px; line-height: 1.6; margin: 0;">
                        Dear {supplier_name} Team,
                    </p>

                    <div style="color: #333; font-size: 14px; line-height: 1.6;
                                margin: 16px 0; white-space: pre-line;">
                        {body}
                    </div>

                    {requirements_block}
                </div>

                <!-- Footer -->
                <div style="background-color: #f8f9fa; padding: 16px 32px;
                            border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #888; font-size: 11px;">
                        Sent via Tamkin &middot; AI-Powered Procurement
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


class EmailQueue:
    """Simple in-memory email queue with rate limiting.

    Tracks sent emails by their Resend email ID for delivery status tracking.
    """

    def __init__(self, rate_limit_per_second: float = 0.5):
        self._queue: deque[dict[str, Any]] = deque()
        self._sent: dict[str, dict[str, Any]] = {}  # email_id → metadata
        self._rate_limit = rate_limit_per_second
        self._last_sent_at: float = 0

    def enqueue(self, to: str, subject: str, body_html: str, metadata: dict | None = None) -> None:
        """Add an email to the queue."""
        self._queue.append({
            "to": to,
            "subject": subject,
            "body_html": body_html,
            "metadata": metadata or {},
            "queued_at": time.time(),
        })

    async def process_next(self) -> dict | None:
        """Send the next email in the queue, respecting rate limits.

        Returns the send result or None if queue is empty or rate-limited.
        """
        if not self._queue:
            return None

        # Rate limit check
        elapsed = time.time() - self._last_sent_at
        if elapsed < (1.0 / self._rate_limit):
            return None

        item = self._queue.popleft()
        result = await send_email(
            to=item["to"],
            subject=item["subject"],
            body_html=item["body_html"],
            cc=item["metadata"].get("cc"),
            reply_to=item["metadata"].get("reply_to"),
            headers=item["metadata"].get("headers"),
        )

        self._last_sent_at = time.time()

        # Track by email ID for delivery status
        email_id = result.get("id")
        if email_id and result.get("sent"):
            self._sent[email_id] = {
                **item["metadata"],
                "to": item["to"],
                "subject": item["subject"],
                "sent_at": self._last_sent_at,
            }

        return result

    async def process_all(self) -> list[dict]:
        """Process all queued emails with rate limiting.

        Returns list of send results.
        """
        import asyncio

        results = []
        while self._queue:
            result = await self.process_next()
            if result is None:
                # Rate limited — wait and retry
                await asyncio.sleep(1.0 / self._rate_limit)
                continue
            results.append(result)
        return results

    def get_metadata_by_email_id(self, email_id: str) -> dict | None:
        """Look up metadata for a sent email by its Resend email ID."""
        return self._sent.get(email_id)

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def sent_count(self) -> int:
        return len(self._sent)
