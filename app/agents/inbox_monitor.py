"""Inbox Monitor — poll email inboxes for supplier responses.

Currently implements:
- GmailMonitor: Uses Gmail API with OAuth2 to check for RFQ responses
- IMAPMonitor: Placeholder for generic IMAP provider

The monitor does NOT auto-process responses. It returns raw messages
for the outreach endpoint to display and the response parser to handle.
"""

import base64
import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class InboxMonitor:
    """Base class for inbox monitoring providers."""

    async def start_monitoring(self, config: dict, project_id: str) -> None:
        """Start polling an inbox for responses to a specific project's outreach."""
        raise NotImplementedError("Inbox monitoring not yet implemented")

    async def stop_monitoring(self, project_id: str) -> None:
        """Stop monitoring for a specific project."""
        raise NotImplementedError("Inbox monitoring not yet implemented")

    async def check_once(self, config: dict, project_id: str) -> list[dict]:
        """One-shot check: look for new responses matching a project's outreach.

        Returns:
            List of dicts with keys: sender, subject, body, received_at, matched_supplier
        """
        raise NotImplementedError("Inbox monitoring not yet implemented")


class GmailMonitor(InboxMonitor):
    """Gmail-based inbox monitor using Gmail API.

    Uses OAuth2 credentials to access the user's Gmail inbox and search
    for recent emails that match RFQ response patterns.

    Required config keys:
    - gmail_credentials_json: Path to OAuth2 client credentials JSON
    - gmail_token_json: Path to stored OAuth2 token
    - supplier_emails: list of known supplier email addresses/domains
    - max_results: max messages to return (default: 20)
    """

    async def check_once(self, config: dict, project_id: str) -> list[dict]:
        """Check Gmail for recent supplier responses."""
        settings = get_settings()

        credentials_json = config.get("credentials_json") or settings.gmail_credentials_json
        token_json = config.get("token_json") or settings.gmail_token_json

        if not credentials_json or not token_json:
            logger.warning("Gmail credentials not configured — skipping inbox check")
            return []

        try:
            service = self._build_gmail_service(credentials_json, token_json)
        except Exception as e:
            logger.error("Failed to build Gmail service: %s", e)
            return []

        # Build search query for RFQ responses
        supplier_emails = config.get("supplier_emails", [])
        supplier_domains = config.get("supplier_domains", [])
        max_results = config.get("max_results", 20)

        query_parts = []

        # Search for replies and quotes
        subject_terms = ["Re:", "Quote", "Quotation", "Pricing", "RFQ", "Inquiry"]
        subject_query = " OR ".join(f"subject:{term}" for term in subject_terms)
        query_parts.append(f"({subject_query})")

        # Filter by known supplier emails/domains
        if supplier_emails:
            from_query = " OR ".join(f"from:{email}" for email in supplier_emails)
            query_parts.append(f"({from_query})")
        elif supplier_domains:
            from_query = " OR ".join(f"from:@{domain}" for domain in supplier_domains)
            query_parts.append(f"({from_query})")

        # Only recent messages (last 7 days)
        query_parts.append("newer_than:7d")

        # Only unread
        query_parts.append("is:unread")

        search_query = " ".join(query_parts)
        logger.info("Gmail search query: %s", search_query)

        try:
            results = service.users().messages().list(
                userId="me",
                q=search_query,
                maxResults=max_results,
            ).execute()

            messages = results.get("messages", [])
            if not messages:
                logger.info("No matching emails found in Gmail")
                return []

            parsed_messages = []
            for msg_ref in messages:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="full",
                ).execute()

                parsed = self._parse_gmail_message(msg)
                if parsed:
                    # Try to match to a known supplier
                    parsed["matched_supplier"] = self._match_supplier(
                        parsed.get("sender", ""),
                        supplier_emails,
                        supplier_domains,
                    )
                    parsed_messages.append(parsed)

            logger.info("Found %d matching emails in Gmail", len(parsed_messages))
            return parsed_messages

        except Exception as e:
            logger.error("Gmail inbox check failed: %s", e)
            return []

    def _build_gmail_service(self, credentials_json: str, token_json: str) -> Any:
        """Build an authenticated Gmail API service."""
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        # Load token
        creds = None
        try:
            token_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_data)
        except Exception:
            logger.warning("Could not load Gmail token from JSON string")

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())

        if not creds or not creds.valid:
            raise ValueError(
                "Gmail OAuth2 token is invalid or expired. "
                "Please re-authenticate via the Gmail OAuth flow."
            )

        return build("gmail", "v1", credentials=creds)

    def _parse_gmail_message(self, msg: dict) -> dict | None:
        """Parse a Gmail API message into a simple dict."""
        try:
            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

            # Extract body
            body_text = ""
            payload = msg["payload"]

            if payload.get("body", {}).get("data"):
                body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            elif payload.get("parts"):
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                        body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break

            return {
                "message_id": msg["id"],
                "sender": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "body": body_text[:5000],  # Cap at 5K chars
                "received_at": headers.get("date", ""),
                "snippet": msg.get("snippet", ""),
            }
        except Exception as e:
            logger.warning("Failed to parse Gmail message: %s", e)
            return None

    def _match_supplier(
        self,
        sender: str,
        supplier_emails: list[str],
        supplier_domains: list[str],
    ) -> str | None:
        """Try to match a sender to a known supplier email or domain."""
        sender_lower = sender.lower()

        for email in supplier_emails:
            if email.lower() in sender_lower:
                return email

        for domain in supplier_domains:
            if domain.lower() in sender_lower:
                return domain

        return None


class IMAPMonitor(InboxMonitor):
    """IMAP-based inbox monitor for generic email providers.

    Future implementation will use:
    - IMAP IDLE for push-based monitoring
    - Subject line and sender matching against outreach records
    - Configurable poll intervals as fallback
    """
    pass


# Registry of available monitors
MONITOR_REGISTRY: dict[str, type[InboxMonitor]] = {
    "gmail": GmailMonitor,
    "imap": IMAPMonitor,
}


def get_monitor(provider: str) -> InboxMonitor:
    """Get an inbox monitor instance for the given provider.

    Args:
        provider: "gmail" or "imap"

    Returns:
        An InboxMonitor instance.

    Raises:
        ValueError: If provider is not supported.
    """
    cls = MONITOR_REGISTRY.get(provider)
    if not cls:
        raise ValueError(f"Unsupported inbox provider: {provider}. Supported: {list(MONITOR_REGISTRY.keys())}")
    return cls()
