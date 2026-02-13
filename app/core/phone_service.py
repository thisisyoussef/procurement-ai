"""Phone service — Retell AI SDK wrapper for automated supplier calls."""

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RetellPhoneService:
    """Wrapper around the Retell AI SDK for making automated phone calls.

    Retell AI handles:
    - Voice synthesis (multiple voice options)
    - Speech recognition
    - Conversation management (following a script/prompt)
    - Call recording and transcription
    """

    def __init__(self):
        self._client = None

    def _get_client(self) -> Any:
        """Lazy-initialize the Retell client."""
        if self._client is None:
            settings = get_settings()
            if not settings.retell_api_key:
                raise ValueError("RETELL_API_KEY not configured")

            from retell import Retell

            self._client = Retell(api_key=settings.retell_api_key)
        return self._client

    async def create_agent(
        self,
        name: str,
        prompt: str,
        voice_id: str = "11labs-Adrian",
        max_call_duration_seconds: int = 300,
    ) -> dict:
        """Create a Retell AI agent with a custom conversation script.

        Args:
            name: Agent name for identification
            prompt: The conversation script/prompt the agent will follow
            voice_id: Retell voice ID (default: 11labs-Adrian)
            max_call_duration_seconds: Max call length in seconds

        Returns:
            Dict with agent_id and metadata
        """
        try:
            client = self._get_client()
            agent = client.agent.create(
                response_engine={
                    "type": "retell-llm",
                    "llm_id": None,  # Use inline prompt
                },
                agent_name=name,
                voice_id=voice_id,
                language="en-US",
                opt_out_sensitive_data_storage=False,
                max_call_duration_ms=max_call_duration_seconds * 1000,
                enable_backchannel=True,
                begin_message=None,  # Agent will use prompt to determine greeting
                general_prompt=prompt,
            )

            agent_id = getattr(agent, "agent_id", str(agent))
            logger.info("Created Retell agent: %s (id=%s)", name, agent_id)
            return {
                "agent_id": agent_id,
                "name": name,
                "voice_id": voice_id,
            }
        except Exception as e:
            logger.error("Failed to create Retell agent: %s", e)
            raise

    async def make_call(
        self,
        agent_id: str,
        phone_number: str,
    ) -> dict:
        """Initiate an outbound phone call.

        Args:
            agent_id: The Retell agent ID to use for the call
            phone_number: Phone number to call (E.164 format, e.g., +14155551234)

        Returns:
            Dict with call_id and initial status
        """
        try:
            client = self._get_client()

            # Ensure phone number is in E.164 format
            if not phone_number.startswith("+"):
                phone_number = f"+1{phone_number}"  # Assume US if no country code

            call = client.call.create_phone_call(
                from_number=None,  # Use Retell's default outbound number
                to_number=phone_number,
                override_agent_id=agent_id,
            )

            call_id = getattr(call, "call_id", str(call))
            logger.info("Initiated Retell call: %s to %s", call_id, phone_number)
            return {
                "call_id": call_id,
                "status": "initiated",
                "phone_number": phone_number,
            }
        except Exception as e:
            logger.error("Failed to initiate Retell call to %s: %s", phone_number, e)
            raise

    async def get_call_status(self, call_id: str) -> dict:
        """Get the current status of a phone call.

        Args:
            call_id: The Retell call ID

        Returns:
            Dict with status, duration, transcript, and recording_url
        """
        try:
            client = self._get_client()
            call = client.call.retrieve(call_id)

            # Extract call data from Retell response
            status = getattr(call, "call_status", "unknown")
            transcript = getattr(call, "transcript", "")
            recording_url = getattr(call, "recording_url", None)
            duration_ms = getattr(call, "duration_ms", 0)
            start_timestamp = getattr(call, "start_timestamp", None)
            end_timestamp = getattr(call, "end_timestamp", None)

            # Map Retell statuses to our statuses
            status_map = {
                "registered": "pending",
                "ongoing": "in_progress",
                "ended": "completed",
                "error": "failed",
            }

            return {
                "call_id": call_id,
                "status": status_map.get(status, status),
                "duration_seconds": (duration_ms or 0) / 1000.0,
                "transcript": transcript,
                "recording_url": recording_url,
                "started_at": str(start_timestamp) if start_timestamp else None,
                "ended_at": str(end_timestamp) if end_timestamp else None,
            }
        except Exception as e:
            logger.error("Failed to get call status for %s: %s", call_id, e)
            raise

    async def list_calls(self, limit: int = 50) -> list[dict]:
        """List recent calls.

        Args:
            limit: Maximum number of calls to return

        Returns:
            List of call status dicts
        """
        try:
            client = self._get_client()
            calls = client.call.list()

            results = []
            for call in (calls or [])[:limit]:
                call_id = getattr(call, "call_id", "")
                status = getattr(call, "call_status", "unknown")
                results.append({
                    "call_id": call_id,
                    "status": status,
                    "duration_seconds": getattr(call, "duration_ms", 0) / 1000.0,
                    "to_number": getattr(call, "to_number", ""),
                    "started_at": str(getattr(call, "start_timestamp", "")),
                })

            return results
        except Exception as e:
            logger.error("Failed to list Retell calls: %s", e)
            return []


# Singleton instance
_phone_service: RetellPhoneService | None = None


def get_phone_service() -> RetellPhoneService:
    """Get the singleton phone service instance."""
    global _phone_service
    if _phone_service is None:
        _phone_service = RetellPhoneService()
    return _phone_service
