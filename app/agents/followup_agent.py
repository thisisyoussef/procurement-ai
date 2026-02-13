"""Agent E: Follow-up — generates follow-up emails for non-responsive suppliers."""

import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.schemas.agent_state import (
    FollowUpEmail,
    FollowUpResult,
    OutreachState,
    ParsedRequirements,
)

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "followup.md").read_text()


async def generate_follow_ups(
    outreach_state: OutreachState,
    requirements: ParsedRequirements,
) -> FollowUpResult:
    """Generate follow-up emails for non-responsive suppliers."""
    # Find non-responsive suppliers that need follow-ups
    non_responsive = []
    for status in outreach_state.supplier_statuses:
        if status.email_sent and not status.response_received and status.follow_ups_sent < 3:
            non_responsive.append({
                "supplier_name": status.supplier_name,
                "supplier_index": status.supplier_index,
                "follow_up_number": status.follow_ups_sent + 1,
            })

    if not non_responsive:
        logger.info("No non-responsive suppliers need follow-ups")
        return FollowUpResult(summary="All suppliers have responded or reached follow-up limit")

    logger.info("Generating follow-ups for %d non-responsive suppliers", len(non_responsive))

    req_context = {
        "product_type": requirements.product_type,
        "quantity": requirements.quantity,
        "delivery_location": requirements.delivery_location,
    }

    prompt = f"""Generate follow-up emails for these non-responsive suppliers.

## Product Context
{json.dumps(req_context, indent=2)}

## Non-responsive Suppliers
{json.dumps(non_responsive, indent=2)}

Each entry includes the follow_up_number (1=day 3 gentle, 2=day 7 urgent, 3=day 14 final).
Generate one follow-up email per supplier at the appropriate urgency level.

Return JSON matching the output format in your instructions."""

    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_cheap,
        max_tokens=3000,
    )

    # Parse response
    try:
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            logger.error("Failed to parse follow-up agent response")
            return FollowUpResult(summary="Failed to parse LLM response")

    follow_ups = []
    for fu in data.get("follow_ups", []):
        try:
            follow_ups.append(FollowUpEmail(
                supplier_name=fu.get("supplier_name", "Unknown"),
                supplier_index=fu.get("supplier_index", 0),
                recipient_email=fu.get("recipient_email"),
                subject=fu.get("subject", "Follow-up: RFQ Inquiry"),
                body=fu.get("body", ""),
                follow_up_number=fu.get("follow_up_number", 1),
                status="draft",
            ))
        except Exception:
            continue

    logger.info("Generated %d follow-up emails", len(follow_ups))
    return FollowUpResult(
        follow_ups=follow_ups,
        summary=data.get("summary", f"Generated {len(follow_ups)} follow-ups"),
    )
