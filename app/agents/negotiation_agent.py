"""Agent G: Negotiation — evaluates supplier quotes and drafts intelligent responses.

When the response parser extracts a quote, this agent:
1. Evaluates the quote against requirements and budget
2. Compares against other received quotes
3. Generates one of four responses: accept, clarify, counter, or reject
4. Drafts a response email ready for sending
"""

import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.schemas.agent_state import (
    DraftEmail,
    NegotiationResponse,
    NegotiationResult,
    ParsedQuote,
    ParsedRequirements,
)

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "negotiation.md").read_text()


async def evaluate_and_respond(
    quote: ParsedQuote,
    requirements: ParsedRequirements,
    all_quotes: list[ParsedQuote] | None = None,
) -> NegotiationResponse:
    """Evaluate a supplier's quote and generate a negotiation response.

    Args:
        quote: The parsed quote to evaluate.
        requirements: The buyer's parsed requirements.
        all_quotes: All quotes received so far (for competitive context).

    Returns:
        NegotiationResponse with action, reasoning, and draft email.
    """
    logger.info("Evaluating quote from %s", quote.supplier_name)

    # Build context for the LLM
    quote_context = {
        "supplier_name": quote.supplier_name,
        "unit_price": quote.unit_price,
        "currency": quote.currency,
        "moq": quote.moq,
        "lead_time": quote.lead_time,
        "payment_terms": quote.payment_terms,
        "shipping_terms": quote.shipping_terms,
        "validity_period": quote.validity_period,
        "notes": quote.notes,
        "confidence_score": quote.confidence_score,
    }

    req_context = {
        "product_type": requirements.product_type,
        "material": requirements.material,
        "quantity": requirements.quantity,
        "budget_range": requirements.budget_range,
        "delivery_location": requirements.delivery_location,
        "deadline": str(requirements.deadline) if requirements.deadline else None,
        "certifications_needed": requirements.certifications_needed,
    }

    # Competitive context (anonymized)
    competitive_context = None
    if all_quotes and len(all_quotes) > 1:
        other_quotes = [q for q in all_quotes if q.supplier_name != quote.supplier_name]
        if other_quotes:
            competitive_context = {
                "total_quotes_received": len(all_quotes),
                "other_prices": [q.unit_price for q in other_quotes if q.unit_price],
                "other_lead_times": [q.lead_time for q in other_quotes if q.lead_time],
            }

    prompt = f"""Evaluate this supplier quote and decide how to respond.

## Buyer's Requirements
{json.dumps(req_context, indent=2)}

## Supplier's Quote
{json.dumps(quote_context, indent=2)}

## Raw Quote Text
{quote.raw_text[:2000] if quote.raw_text else "Not available"}
"""

    if competitive_context:
        prompt += f"""
## Competitive Context (anonymized)
{json.dumps(competitive_context, indent=2)}
"""

    prompt += """
Evaluate the quote and return JSON matching the output format in your instructions.
Choose the appropriate action (accept, clarify, counter, reject) based on your decision framework."""

    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=2000,
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
            logger.error("Failed to parse negotiation agent response")
            return NegotiationResponse(
                supplier_name=quote.supplier_name,
                supplier_index=quote.supplier_index,
                action="clarify",
                reasoning="Could not generate automated response — manual review recommended",
                confidence=0.0,
            )

    # Build draft email from LLM response
    email_data = data.get("email", {})
    draft = None
    if email_data.get("body"):
        draft = DraftEmail(
            supplier_name=quote.supplier_name,
            supplier_index=quote.supplier_index,
            subject=email_data.get("subject", f"Re: RFQ — {requirements.product_type}"),
            body=email_data["body"],
            status="auto_queued",
        )

    action = data.get("action", "clarify")
    response = NegotiationResponse(
        supplier_name=quote.supplier_name,
        supplier_index=quote.supplier_index,
        action=action,
        reasoning=data.get("reasoning", ""),
        draft_email=draft,
        confidence=data.get("confidence", 50.0),
    )

    logger.info(
        "Negotiation for %s: action=%s, confidence=%.0f",
        quote.supplier_name, action, response.confidence,
    )
    return response


async def evaluate_all_quotes(
    quotes: list[ParsedQuote],
    requirements: ParsedRequirements,
) -> NegotiationResult:
    """Evaluate all received quotes and generate responses for each.

    Args:
        quotes: All parsed quotes from supplier responses.
        requirements: The buyer's parsed requirements.

    Returns:
        NegotiationResult with responses for each quote.
    """
    if not quotes:
        return NegotiationResult(summary="No quotes to evaluate")

    logger.info("Evaluating %d quotes for negotiation", len(quotes))

    responses = []
    for quote in quotes:
        try:
            response = await evaluate_and_respond(
                quote=quote,
                requirements=requirements,
                all_quotes=quotes,
            )
            responses.append(response)
        except Exception as e:
            logger.error("Negotiation failed for %s: %s", quote.supplier_name, e)

    # Build summary
    actions = [r.action for r in responses]
    summary_parts = []
    for action in ["accept", "counter", "clarify", "reject"]:
        count = actions.count(action)
        if count:
            summary_parts.append(f"{count} {action}")

    summary = f"Evaluated {len(quotes)} quotes: {', '.join(summary_parts)}"
    logger.info("Negotiation complete: %s", summary)

    return NegotiationResult(responses=responses, summary=summary)
