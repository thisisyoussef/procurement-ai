"""Agent D: Outreach — drafts personalized RFQ emails for shortlisted suppliers.

Includes:
- Manual draft generation for selected suppliers
- Auto-draft and queue for suppliers above a verification threshold
- Batch execution infrastructure for autonomous sending
"""

import asyncio
import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.schemas.agent_state import (
    AutoOutreachConfig,
    DraftEmail,
    DiscoveredSupplier,
    OutreachResult,
    ParsedRequirements,
    RecommendationResult,
    SupplierVerification,
    VerificationResults,
)

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "outreach.md").read_text()


async def draft_outreach_emails(
    selected_suppliers: list[DiscoveredSupplier],
    requirements: ParsedRequirements,
    recommendations: RecommendationResult,
) -> OutreachResult:
    """Draft personalized RFQ emails for selected suppliers."""
    logger.info("Drafting outreach emails for %d suppliers", len(selected_suppliers))

    # Build supplier context for the LLM
    supplier_summaries = []
    for i, s in enumerate(selected_suppliers):
        summary = {
            "index": i,
            "name": s.name,
            "website": s.website,
            "email": s.email,
            "city": s.city,
            "country": s.country,
            "description": s.description,
            "categories": s.categories,
            "certifications": s.certifications,
            "google_rating": s.google_rating,
        }
        supplier_summaries.append(summary)

    # Build requirements context
    req_context = {
        "product_type": requirements.product_type,
        "material": requirements.material,
        "dimensions": requirements.dimensions,
        "quantity": requirements.quantity,
        "customization": requirements.customization,
        "delivery_location": requirements.delivery_location,
        "deadline": str(requirements.deadline) if requirements.deadline else None,
        "certifications_needed": requirements.certifications_needed,
        "budget_range": requirements.budget_range,
    }

    prompt = f"""Draft personalized RFQ emails for these suppliers based on the product requirements.

## Product Requirements
{json.dumps(req_context, indent=2)}

## Selected Suppliers
{json.dumps(supplier_summaries, indent=2)}

Draft one email per supplier. Personalize each email by referencing the supplier's
specific capabilities, certifications, or specialties from their profile.

Return JSON matching the output format in your instructions."""

    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=4096,
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
            logger.error("Failed to parse outreach agent response")
            return OutreachResult(summary="Failed to parse LLM response")

    drafts = []
    for d in data.get("drafts", []):
        try:
            drafts.append(DraftEmail(
                supplier_name=d.get("supplier_name", "Unknown"),
                supplier_index=d.get("supplier_index", 0),
                recipient_email=d.get("recipient_email"),
                subject=d.get("subject", "RFQ Inquiry"),
                body=d.get("body", ""),
                status="draft",
            ))
        except Exception:
            continue

    logger.info("Drafted %d outreach emails", len(drafts))
    return OutreachResult(
        drafts=drafts,
        summary=data.get("summary", f"Drafted {len(drafts)} RFQ emails"),
    )


async def auto_draft_and_queue(
    verified_suppliers: list[DiscoveredSupplier],
    verifications: VerificationResults,
    requirements: ParsedRequirements,
    recommendations: RecommendationResult,
    auto_config: AutoOutreachConfig,
) -> OutreachResult:
    """Auto-draft and queue RFQ emails for high-scoring suppliers.

    Filters suppliers above `auto_config.auto_send_threshold` verification
    score, generates drafts via the standard drafting flow, and marks them
    as "auto_queued" (not sent yet — requires explicit send step).

    Args:
        verified_suppliers: All discovered suppliers
        verifications: Verification results with composite scores
        requirements: Parsed requirements
        recommendations: Recommendation output
        auto_config: Auto outreach configuration

    Returns:
        OutreachResult with drafts marked as "auto_queued"
    """
    threshold = auto_config.auto_send_threshold
    logger.info(
        "Auto-drafting outreach: threshold=%.0f, max_concurrent=%d",
        threshold, auto_config.max_concurrent_outreach,
    )

    # Build a map of supplier_name → verification score
    score_map: dict[str, float] = {}
    for v in verifications.verifications:
        score_map[v.supplier_name] = v.composite_score

    # Filter suppliers above threshold
    eligible = [
        s for s in verified_suppliers
        if score_map.get(s.name, 0) >= threshold
    ]

    if not eligible:
        logger.info("No suppliers above threshold %.0f — nothing to auto-draft", threshold)
        return OutreachResult(
            drafts=[],
            summary=f"No suppliers met the auto-send threshold of {threshold}",
        )

    # Cap to max_concurrent_outreach
    eligible = eligible[:auto_config.max_concurrent_outreach]
    logger.info("Auto-drafting for %d eligible suppliers", len(eligible))

    # Use standard drafting flow
    result = await draft_outreach_emails(eligible, requirements, recommendations)

    # Mark all drafts as auto_queued
    for draft in result.drafts:
        draft.status = "auto_queued"

    result.summary = f"Auto-queued {len(result.drafts)} RFQ emails (threshold: {threshold}+)"
    return result


async def execute_outreach_batch(
    drafts: list[DraftEmail],
    email_service: object,
    rate_limit_seconds: float = 2.0,
) -> list[DraftEmail]:
    """Execute a batch of queued outreach emails with rate limiting.

    This is the autonomous sending step — only called after auto_draft_and_queue
    with explicit user authorization.

    Args:
        drafts: List of draft emails to send (status should be "auto_queued")
        email_service: Email sending service instance with async send_email() method
        rate_limit_seconds: Minimum seconds between sends (default: 2.0)

    Returns:
        Updated drafts with status set to "sent" or "failed"
    """
    logger.info("Executing outreach batch: %d emails", len(drafts))

    for i, draft in enumerate(drafts):
        if draft.status != "auto_queued":
            continue

        try:
            # Resolve recipient
            recipient = draft.recipient_email
            if not recipient:
                draft.status = "failed"
                logger.warning("No email for %s — skipping", draft.supplier_name)
                continue

            result = await email_service.send_email(  # type: ignore[attr-defined]
                to=recipient,
                subject=draft.subject,
                body_html=draft.body,
            )

            if result.get("sent"):
                draft.status = "sent"
                logger.info("  ✅ Sent to %s (%s)", draft.supplier_name, recipient)
            else:
                draft.status = "failed"
                logger.warning("  ❌ Failed for %s: %s", draft.supplier_name, result.get("error"))

        except Exception as e:
            draft.status = "failed"
            logger.error("  ❌ Exception sending to %s: %s", draft.supplier_name, e)

        # Rate limiting between sends
        if i < len(drafts) - 1:
            await asyncio.sleep(rate_limit_seconds)

    sent_count = sum(1 for d in drafts if d.status == "sent")
    failed_count = sum(1 for d in drafts if d.status == "failed")
    logger.info("Batch complete: %d sent, %d failed", sent_count, failed_count)

    return drafts
