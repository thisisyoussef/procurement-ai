"""Phone calling agent — automated supplier outreach via Retell AI.

This agent:
1. Generates a customized conversation script for each supplier
2. Initiates phone calls via Retell AI
3. Parses call transcripts to extract pricing, MOQ, lead time
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.core.phone_service import get_phone_service
from app.schemas.agent_state import (
    ParsedCallResult,
    ParsedRequirements,
    PhoneCallStatus,
)

logger = logging.getLogger(__name__)
settings = get_settings()

SCRIPT_TEMPLATE = (Path(__file__).parent / "prompts" / "phone_agent.md").read_text()


async def create_call_script(
    supplier_name: str,
    requirements: ParsedRequirements,
    custom_questions: list[str] | None = None,
    company_name: str = "Procurement AI",
) -> str:
    """Generate a customized phone conversation script for a specific supplier.

    Uses Haiku LLM to adapt the base template with supplier-specific details
    and any custom questions the user wants to ask.

    Returns:
        The complete conversation script as a string
    """
    # Fill in template variables
    script = SCRIPT_TEMPLATE.format(
        supplier_name=supplier_name,
        product_type=requirements.product_type,
        company_name=company_name,
        quantity=requirements.quantity or "a bulk order",
        customization_type=requirements.customization or "specifications",
        certifications=", ".join(requirements.certifications_needed) or "industry standard",
        custom_questions="\n".join(
            f"- {q}" for q in (custom_questions or [])
        ) or "None specified",
    )

    # Use Haiku to refine the script for this specific supplier
    prompt = f"""Given this phone call script template, refine it to sound natural and
conversational for calling {supplier_name} about {requirements.product_type}.

Keep the same structure but make it sound like a real person would say it.
Remove any template artifacts like curly braces.

Template:
{script}

Return ONLY the refined script text. No JSON wrapping."""

    try:
        refined = await call_llm_structured(
            prompt=prompt,
            system="You refine phone conversation scripts to sound natural. Return only the refined script.",
            model=settings.model_cheap,
            max_tokens=1500,
        )
        return refined.strip()
    except Exception as e:
        logger.warning("Failed to refine call script, using template: %s", e)
        return script


async def initiate_supplier_call(
    supplier_name: str,
    supplier_index: int,
    phone_number: str,
    requirements: ParsedRequirements,
    custom_questions: list[str] | None = None,
    voice_id: str = "11labs-Adrian",
    max_duration: int = 300,
) -> PhoneCallStatus:
    """Create an AI agent and initiate a phone call to a supplier.

    Args:
        supplier_name: Name of the supplier to call
        supplier_index: Index in discovery results
        phone_number: Phone number (E.164 format preferred)
        requirements: Parsed requirements for context
        custom_questions: Optional list of custom questions
        voice_id: Retell voice ID
        max_duration: Max call duration in seconds

    Returns:
        PhoneCallStatus with the call_id and initial status
    """
    phone_service = get_phone_service()

    # Generate customized script
    script = await create_call_script(
        supplier_name=supplier_name,
        requirements=requirements,
        custom_questions=custom_questions,
    )

    # Create a Retell agent for this call
    agent_result = await phone_service.create_agent(
        name=f"Procurement AI — {supplier_name}",
        prompt=script,
        voice_id=voice_id,
        max_call_duration_seconds=max_duration,
    )

    # Initiate the call
    call_result = await phone_service.make_call(
        agent_id=agent_result["agent_id"],
        phone_number=phone_number,
    )

    logger.info(
        "Initiated call to %s (%s): call_id=%s",
        supplier_name, phone_number, call_result["call_id"],
    )

    return PhoneCallStatus(
        call_id=call_result["call_id"],
        supplier_name=supplier_name,
        supplier_index=supplier_index,
        status="pending",
    )


async def get_call_detail(call_id: str) -> dict[str, Any]:
    """Get detailed status of a phone call including transcript.

    Returns:
        Dict with status, duration, transcript, recording_url
    """
    phone_service = get_phone_service()
    return await phone_service.get_call_status(call_id)


async def parse_call_transcript(
    transcript: str,
    supplier_name: str,
    call_id: str,
) -> ParsedCallResult:
    """Parse a phone call transcript to extract structured procurement data.

    Uses Haiku LLM to extract pricing, MOQ, lead time, and key findings
    from the raw transcript.

    Args:
        transcript: The raw call transcript text
        supplier_name: Name of the supplier
        call_id: ID of the call

    Returns:
        ParsedCallResult with structured data
    """
    if not transcript or len(transcript.strip()) < 20:
        return ParsedCallResult(
            supplier_name=supplier_name,
            call_id=call_id,
            key_findings=["Call transcript too short or empty"],
            raw_transcript=transcript or "",
        )

    prompt = f"""Analyze this phone call transcript with supplier "{supplier_name}" and extract key procurement information.

TRANSCRIPT:
{transcript[:5000]}

Return a JSON object with:
{{
    "pricing_info": "unit price or pricing details mentioned, or null",
    "moq": "minimum order quantity mentioned, or null",
    "lead_time": "lead time / delivery timeline mentioned, or null",
    "key_findings": ["list", "of", "important", "takeaways"],
    "follow_up_needed": true/false,
    "contact_email": "email mentioned during call, or null"
}}

If information was not discussed or unclear, set it to null.
Return ONLY valid JSON."""

    try:
        response = await call_llm_structured(
            prompt=prompt,
            system="You extract structured procurement data from phone call transcripts. Return only valid JSON.",
            model=settings.model_cheap,
            max_tokens=1000,
        )

        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]

        data = json.loads(text)

        return ParsedCallResult(
            supplier_name=supplier_name,
            call_id=call_id,
            pricing_info=data.get("pricing_info"),
            moq=data.get("moq"),
            lead_time=data.get("lead_time"),
            key_findings=data.get("key_findings", []),
            follow_up_needed=data.get("follow_up_needed", False),
            raw_transcript=transcript,
        )

    except Exception as e:
        logger.error("Failed to parse call transcript: %s", e)
        return ParsedCallResult(
            supplier_name=supplier_name,
            call_id=call_id,
            key_findings=[f"Transcript parsing failed: {str(e)}"],
            raw_transcript=transcript,
        )
