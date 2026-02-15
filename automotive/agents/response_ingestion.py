"""Agent 7 — Response Ingestion & Quote Structuring.

Monitors incoming email responses, extracts quote data from various
formats (PDF, Excel, email body), and normalizes into comparable structure.
"""

import logging
from typing import Any

from automotive.core.config import MODEL_TIER_BALANCED, MODEL_TIER_CHEAP
from automotive.core.llm import call_llm_structured
from automotive.schemas.quotes import ParsedQuote, QuoteIngestionResult
from automotive.schemas.rfq import RFQResult

logger = logging.getLogger(__name__)

QUOTE_EXTRACTION_PROMPT = """\
You are Tamkin's Quote Extraction Agent for automotive procurement.

Extract structured pricing data from supplier quote responses. The input
may be raw text from a PDF, Excel data, or an email body.

Extract with HIGH PRECISION — pricing errors are catastrophic. For any
field where you are less than 95% confident in the extracted value,
add that field name to low_confidence_fields.

Key fields to extract:
- piece_price: Per-unit cost at the quoted volume
- tooling_cost: One-time tooling/mold/die cost
- production_lead_time_weeks: Weeks from order to first production delivery
- moq: Minimum order quantity
- material_cost, labor_cost, overhead_cost: If cost breakdown provided
- shipping_terms: FOB, CIF, DDP, etc.

Normalize all prices to the stated currency. If the quote uses a different
currency than USD, note it but do NOT convert — we'll convert separately.

For every extracted number, verify it makes physical sense:
- Piece prices for metal parts are typically $0.10–$50.00
- Tooling for stamping: $50K–$300K
- Tooling for die casting: $100K–$500K
- Lead times: 2–24 weeks
- MOQs: 50–100,000 depending on part type
"""


async def parse_quote_from_text(
    raw_text: str,
    supplier_id: str,
    supplier_name: str,
    rfq_context: dict | None = None,
) -> ParsedQuote:
    """Parse a single quote from raw text (email body, PDF text, etc.)."""
    schema = {
        "type": "object",
        "properties": {
            "piece_price": {"type": "number"},
            "piece_price_currency": {"type": "string"},
            "price_breaks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "volume": {"type": "integer"},
                        "price": {"type": "number"},
                    },
                },
            },
            "material_cost": {"type": ["number", "null"]},
            "labor_cost": {"type": ["number", "null"]},
            "overhead_cost": {"type": ["number", "null"]},
            "sga_cost": {"type": ["number", "null"]},
            "profit_margin": {"type": ["number", "null"]},
            "tooling_cost": {"type": ["number", "null"]},
            "tooling_lead_time_weeks": {"type": ["integer", "null"]},
            "tool_life_shots": {"type": ["integer", "null"]},
            "tooling_ownership": {"type": ["string", "null"]},
            "production_lead_time_weeks": {"type": ["integer", "null"]},
            "moq": {"type": ["integer", "null"]},
            "shipping_terms": {"type": ["string", "null"]},
            "extraction_confidence": {"type": "number"},
            "low_confidence_fields": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["piece_price", "piece_price_currency", "extraction_confidence"],
    }

    context_text = ""
    if rfq_context:
        context_text = (
            f"\nOriginal RFQ context:\n"
            f"Part: {rfq_context.get('part_description', '')}\n"
            f"Volume: {rfq_context.get('annual_volume', '')}/year\n"
        )

    user_msg = f"Extract quote data from this supplier response:\n\n{raw_text}{context_text}"

    try:
        result = await call_llm_structured(
            system=QUOTE_EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_CHEAP,
            max_tokens=2048,
        )

        piece_price = result.get("piece_price", 0)
        annual_volume = rfq_context.get("annual_volume", 0) if rfq_context else 0
        tooling = result.get("tooling_cost") or 0

        # Calculate TCO
        annual_piece_cost = piece_price * annual_volume
        # Amortize tooling over 3 years
        annual_tooling = tooling / 3 if tooling else 0
        tco = annual_piece_cost + annual_tooling

        return ParsedQuote(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            piece_price=piece_price,
            piece_price_currency=result.get("piece_price_currency", "USD"),
            price_breaks=result.get("price_breaks", []),
            material_cost=result.get("material_cost"),
            labor_cost=result.get("labor_cost"),
            overhead_cost=result.get("overhead_cost"),
            sga_cost=result.get("sga_cost"),
            profit_margin=result.get("profit_margin"),
            tooling_cost=result.get("tooling_cost"),
            tooling_lead_time_weeks=result.get("tooling_lead_time_weeks"),
            tool_life_shots=result.get("tool_life_shots"),
            tooling_ownership=result.get("tooling_ownership"),
            production_lead_time_weeks=result.get("production_lead_time_weeks"),
            moq=result.get("moq"),
            shipping_terms=result.get("shipping_terms"),
            normalized_piece_price_usd=piece_price,
            estimated_annual_tco_usd=round(tco, 2),
            extraction_confidence=result.get("extraction_confidence", 0.5),
            low_confidence_fields=result.get("low_confidence_fields", []),
            notes=result.get("notes", []),
        )

    except Exception:
        logger.exception("Quote parsing failed for %s", supplier_name)
        return ParsedQuote(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            extraction_confidence=0.0,
            low_confidence_fields=["all"],
            notes=["Automated extraction failed — manual review required"],
        )


async def run(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point.

    Processes quotes from three sources:
    1. Already-parsed quotes in state (from webhook handler)
    2. Raw quote texts attached to state (from manual paste or email body)
    3. RFQ outreach records — generates placeholder entries for suppliers
       that were sent RFQs but haven't responded yet
    """
    rfq_data = state.get("rfq_result", {})
    existing_quotes = state.get("quote_ingestion", {})
    raw_quotes = state.get("raw_quote_texts", [])  # list of {supplier_id, supplier_name, text}
    req_data = state.get("parsed_requirement", {})

    # Start with any already-parsed quotes
    parsed: list[ParsedQuote] = []
    if existing_quotes:
        for q in existing_quotes.get("quotes", []):
            parsed.append(ParsedQuote(**q) if isinstance(q, dict) else q)

    # Parse any raw quote texts that arrived (from webhook or manual input)
    rfq_context = {
        "part_description": req_data.get("part_description", ""),
        "annual_volume": req_data.get("annual_volume", 0),
    } if req_data else None

    for raw in raw_quotes:
        if not raw.get("text"):
            continue
        quote = await parse_quote_from_text(
            raw_text=raw["text"],
            supplier_id=raw.get("supplier_id", "unknown"),
            supplier_name=raw.get("supplier_name", "Unknown"),
            rfq_context=rfq_context,
        )
        parsed.append(quote)

    # Build awaiting list from outreach records
    outreach = rfq_data.get("outreach_records", []) if rfq_data else []
    parsed_supplier_ids = {q.supplier_id for q in parsed}
    awaiting = [
        r.get("supplier_name", r.get("supplier_id", ""))
        for r in outreach
        if r.get("supplier_id") not in parsed_supplier_ids
        and r.get("delivery_status") in ("sent", "approved", "draft")
    ]

    total_received = len(parsed) + len(raw_quotes)
    logger.info("Quote ingestion: %d parsed, %d awaiting response", len(parsed), len(awaiting))

    return {
        "quote_ingestion": QuoteIngestionResult(
            quotes=parsed,
            total_received=total_received,
            total_parsed=len(parsed),
            awaiting_response=awaiting,
        ).model_dump(),
        "current_stage": "quote_ingest",
        "messages": [{"role": "system", "content": f"Quote ingestion: {len(parsed)} quotes parsed, {len(awaiting)} awaiting response"}],
    }
