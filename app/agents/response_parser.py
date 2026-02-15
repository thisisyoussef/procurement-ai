"""Agent F: Response Parser — extracts structured quote data from supplier replies."""

import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.schemas.buyer_context import BuyerContext
from app.schemas.agent_state import ParsedQuote, ParsedRequirements
from app.schemas.user_profile import UserSourcingProfile

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "response_parser.md").read_text()


async def parse_supplier_response(
    supplier_name: str,
    supplier_index: int,
    response_text: str,
    requirements: ParsedRequirements,
    buyer_context: BuyerContext | None = None,
    user_profile: UserSourcingProfile | None = None,
) -> ParsedQuote:
    """Parse a supplier's email response into structured quote data."""
    logger.info("Parsing response from %s (%d chars)", supplier_name, len(response_text))

    req_context = {
        "product_type": requirements.product_type,
        "quantity": requirements.quantity,
        "material": requirements.material,
    }

    context_block = ""
    if buyer_context:
        context_block += f"\n## Buyer Context\n{buyer_context.model_dump_json(indent=2)}\n"
    if user_profile:
        context_block += f"\n## User Sourcing Profile\n{user_profile.model_dump_json(indent=2)}\n"

    prompt = f"""Extract structured quote data from this supplier's response.
{context_block}

## Supplier: {supplier_name}

## Our Requirements
{json.dumps(req_context, indent=2)}

## Supplier's Response
---
{response_text}
---

Extract all quote fields and assign a confidence score.
Return JSON matching the output format in your instructions."""

    response = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_cheap,
        max_tokens=2000,
    )

    # Parse response
    try:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            logger.error("Failed to parse response parser output")
            return ParsedQuote(
                supplier_name=supplier_name,
                supplier_index=supplier_index,
                confidence_score=0.0,
                raw_text=response_text,
                notes="Failed to parse response",
            )

    quote = ParsedQuote(
        supplier_name=supplier_name,
        supplier_index=supplier_index,
        unit_price=data.get("unit_price"),
        currency=data.get("currency", "USD"),
        moq=data.get("moq"),
        lead_time=data.get("lead_time"),
        payment_terms=data.get("payment_terms"),
        shipping_terms=data.get("shipping_terms"),
        validity_period=data.get("validity_period"),
        notes=data.get("notes"),
        can_fulfill=data.get("can_fulfill"),
        fulfillment_note=data.get("fulfillment_note"),
        confidence_score=data.get("confidence_score", 50.0),
        raw_text=response_text,
    )

    logger.info(
        "Parsed quote from %s: price=%s, MOQ=%s, confidence=%.0f",
        supplier_name, quote.unit_price, quote.moq, quote.confidence_score,
    )
    return quote
