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

    normalized_cc = []
    seen: set[str] = set()
    for candidate in cc or []:
        value = (candidate or "").strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized_cc.append(value)

    if not settings.resend_api_key:
        logger.warning("Resend API key not configured — email not sent to %s", to)
        return {
            "error": "Resend API key not configured",
            "error_type": "missing_api_key",
            "provider": "resend",
            "sent": False,
            "to": to,
            "cc": normalized_cc,
            "from": None,
        }
    from_email = (settings.from_email or "").strip() or "sourcing@asmbl.app"
    if from_email == "sourcing@yourdomain.com":
        logger.warning("FROM_EMAIL is still placeholder value; refusing to send to %s", to)
        return {
            "error": "FROM_EMAIL is not configured (still sourcing@yourdomain.com)",
            "error_type": "invalid_from_email",
            "provider": "resend",
            "sent": False,
            "to": to,
            "cc": normalized_cc,
            "from": from_email,
        }

    try:
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
            return {
                "error": "Resend response missing email id",
                "error_type": "missing_provider_id",
                "provider": "resend",
                "sent": False,
                "to": to,
                "cc": normalized_cc,
                "from": from_email,
                "provider_response": result if isinstance(result, dict) else str(result),
            }
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
            "provider": "resend",
            "to": to,
            "cc": normalized_cc,
            "from": from_email,
        }

    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        logger.error(
            "Failed to send email via Resend to %s (from=%s, cc=%s): %s",
            to,
            from_email,
            ",".join(normalized_cc) if normalized_cc else "-",
            error_message,
            exc_info=True,
        )
        return {
            "error": error_message,
            "error_type": error_type,
            "provider": "resend",
            "sent": False,
            "to": to,
            "cc": normalized_cc,
            "from": from_email,
        }


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


def build_rfq_html(body: str) -> str:
    """Wrap a plain-text RFQ email body in a clean, responsive HTML template.

    Converts the LLM-drafted plain-text body into proper HTML paragraphs.
    Designed to render well across Gmail, Outlook, Apple Mail, and mobile clients.

    Args:
        body: Plain-text email body from the LLM draft (may contain \\n line breaks)

    Returns:
        Full HTML email string with inline CSS
    """
    import html as html_lib

    # Escape HTML entities, then convert double-newlines to paragraphs
    escaped = html_lib.escape(body)
    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
    body_html = "\n".join(
        f'<p style="margin: 0 0 16px 0;">{p.replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RFQ</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f9f9f7;
             font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
             'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <div style="max-width: 600px; margin: 0 auto; padding: 24px 16px;">
        <div style="background-color: #ffffff; border-radius: 8px;
                    border: 1px solid #e8e6e3; overflow: hidden;">

            <!-- Body -->
            <div style="padding: 32px 28px; color: #222222; font-size: 15px;
                        line-height: 1.7;">
                {body_html}
            </div>

            <!-- Footer -->
            <div style="padding: 14px 28px; border-top: 1px solid #eee;">
                <p style="margin: 0; color: #aaa; font-size: 11px;">
                    Sent via Tamkin
                </p>
            </div>
        </div>
    </div>
</body>
</html>"""


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
