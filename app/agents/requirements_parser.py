"""Agent A: Requirements Parser — converts natural language to structured specs.

Enhanced to also generate:
- Regional search strategies with multilingual queries
- Clarifying questions for missing critical information
- Strategic sourcing approach narrative
"""

import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured, call_llm_with_tools
from app.core.progress import emit_progress
from app.schemas.agent_state import ParsedRequirements
from app.schemas.buyer_context import BuyerContext
from app.schemas.user_profile import UserSourcingProfile

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "requirements_parser.md").read_text()

CLARIFICATION_FIELD_ALIASES = {
    "trade_off_priority": "trade_off_priority",
    "priority_tradeoff": "trade_off_priority",
}

CLARIFICATION_TEMPLATES = {
    "quantity": {
        "why_this_question": "Quantity drives supplier fit, MOQ feasibility, and realistic pricing bands.",
        "if_skipped_impact": "Without quantity, shortlist quality drops because MOQ and pricing estimates are less reliable.",
        "suggested_default": "500 units as an initial production run",
    },
    "budget_range": {
        "why_this_question": "Budget keeps recommendations aligned with realistic landed-cost options.",
        "if_skipped_impact": "Without a budget, the shortlist may include suppliers outside your acceptable price range.",
        "suggested_default": "Use market-competitive pricing and prioritize balanced value",
    },
    "delivery_location": {
        "why_this_question": "Delivery location affects freight cost, duties, and timeline estimates.",
        "if_skipped_impact": "Without destination details, landed-cost and lead-time comparisons are less trustworthy.",
        "suggested_default": "Primary warehouse or HQ destination",
    },
    "certifications_needed": {
        "why_this_question": "Certification requirements help filter out suppliers that fail compliance expectations.",
        "if_skipped_impact": "Without compliance constraints, non-qualifying suppliers may appear in top results.",
        "suggested_default": "No mandatory certifications for initial comparison",
    },
    "deadline": {
        "why_this_question": "Deadline defines whether we optimize for speed, risk, or lower cost.",
        "if_skipped_impact": "Without a target timeline, lead-time risk remains uncertain in final recommendations.",
        "suggested_default": "Standard production timeline (6-8 weeks)",
    },
    "trade_off_priority": {
        "why_this_question": "Trade-off preference determines whether to prioritize cost, speed, or risk reduction.",
        "if_skipped_impact": "If priorities are unclear, ranking may not match your decision style.",
        "suggested_default": "Balanced: cost, speed, and quality",
    },
    "_generic": {
        "why_this_question": "This answer improves ranking quality and recommendation confidence.",
        "if_skipped_impact": "Skipping may reduce confidence in the shortlist and increase manual checks later.",
        "suggested_default": "Use the safest reasonable default and continue",
    },
}


def _guess_product_type_from_raw(raw_description: str) -> str:
    raw = raw_description.strip()
    lower = raw.lower()
    anchored_terms = [
        "stamped steel seat bracket",
        "seat bracket",
        "wire harness",
        "inverter housing",
        "battery cooling plate",
        "forged shaft",
        "drivetrain shaft",
    ]
    for term in anchored_terms:
        if term in lower:
            return term

    match = re.search(r"(?:need|looking for|source|find)\s+(?:a|an|the)?\s*([^,.]+)", lower)
    if match:
        candidate = match.group(1).strip()
        candidate = re.sub(r"\b(with|for|to|from)\b.*$", "", candidate).strip()
        candidate = re.sub(r"^\d+[kKmM]?\+?\s*", "", candidate).strip()
        candidate = re.sub(r"\b(units?|pieces?|pcs?)\b", "", candidate).strip()
        candidate = re.sub(r"^custom\s+", "", candidate).strip()
        if candidate:
            return candidate
    return raw[:80]


def _build_default_search_queries(product_type: str) -> list[str]:
    base = product_type.strip()
    if not base:
        return []
    return [
        f"{base} manufacturer",
        f"{base} supplier OEM",
        f"{base} factory wholesale",
        f"{base} contract manufacturing",
        f"{base} production partner",
    ]


def _normalize_clarification_field(field: str | None) -> str:
    normalized = (field or "").strip().lower()
    if not normalized:
        return ""
    return CLARIFICATION_FIELD_ALIASES.get(normalized, normalized)


def _enhance_clarifying_questions(data: dict) -> dict:
    if not settings.feature_focus_circle_search_v1:
        return data

    questions = data.get("clarifying_questions")
    if not isinstance(questions, list):
        return data

    enhanced: list[dict] = []
    for raw_question in questions:
        if not isinstance(raw_question, dict):
            continue
        question = dict(raw_question)
        normalized_field = _normalize_clarification_field(question.get("field"))
        template = CLARIFICATION_TEMPLATES.get(normalized_field, CLARIFICATION_TEMPLATES["_generic"])

        if not question.get("why_this_question"):
            question["why_this_question"] = template["why_this_question"]
        if not question.get("if_skipped_impact"):
            question["if_skipped_impact"] = template["if_skipped_impact"]
        if not question.get("suggested_default"):
            suggestions = question.get("suggestions") or []
            first_suggestion = suggestions[0] if isinstance(suggestions, list) and suggestions else None
            question["suggested_default"] = first_suggestion or template["suggested_default"]
        enhanced.append(question)

    data["clarifying_questions"] = enhanced
    return data


def _apply_domain_guardrails(raw_description: str, data: dict) -> dict:
    """Ensure product_type and search_queries are populated. The LLM handles
    domain-specific logic (automotive certifications, etc.) via the prompt."""
    product_type = str(data.get("product_type") or "").strip()
    if not product_type:
        data["product_type"] = _guess_product_type_from_raw(raw_description)
        product_type = str(data.get("product_type") or "").strip()
    if not data.get("search_queries"):
        data["search_queries"] = _build_default_search_queries(product_type)
    return data


def _requirements_tool_schema() -> list[dict]:
    return [
        {
            "name": "submit_requirements",
            "description": "Submit structured parsed procurement requirements.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_type": {"type": "string"},
                    "material": {"type": ["string", "null"]},
                    "dimensions": {"type": ["string", "null"]},
                    "quantity": {"type": ["integer", "null"]},
                    "customization": {"type": ["string", "null"]},
                    "delivery_location": {"type": ["string", "null"]},
                    "deadline": {"type": ["string", "null"]},
                    "certifications_needed": {"type": "array", "items": {"type": "string"}},
                    "budget_range": {"type": ["string", "null"]},
                    "missing_fields": {"type": "array", "items": {"type": "string"}},
                    "search_queries": {"type": "array", "items": {"type": "string"}},
                    "regional_searches": {"type": "array"},
                    "clarifying_questions": {"type": "array"},
                    "sourcing_strategy": {"type": ["string", "null"]},
                    "sourcing_preference": {"type": ["string", "null"]},
                    "risk_tolerance": {"type": ["string", "null"]},
                    "priority_tradeoff": {"type": ["string", "null"]},
                    "minimum_supplier_count": {"type": ["integer", "null"]},
                    "evidence_strictness": {"type": ["string", "null"]},
                },
                "required": ["product_type"],
                "additionalProperties": True,
            },
        }
    ]


async def parse_requirements(
    raw_description: str,
    buyer_context: BuyerContext | None = None,
    user_profile: UserSourcingProfile | None = None,
) -> ParsedRequirements:
    """Parse a natural language product description into structured requirements.

    Uses Sonnet for enhanced reasoning — regional strategy, clarifying questions,
    and sourcing intelligence require stronger model capabilities.
    """
    logger.info("📋 Parsing requirements from: '%s'", raw_description[:100])
    emit_progress("parsing", "analyzing", "Analyzing your requirements...")

    context_block = ""
    if buyer_context:
        context_block += f"""
Buyer context:
{buyer_context.model_dump_json(indent=2)}
"""
    if user_profile:
        context_block += f"""
User profile:
{user_profile.model_dump_json(indent=2)}
"""

    prompt = f"""Parse the sourcing request into structured JSON using ONLY this user input.

Hard rules:
- Do not use canned examples, defaults, or prior requests as product hints.
- Do not introduce product categories that are not implied by the input.
- Keep `product_type` tightly grounded in the user's wording.
- `search_queries` must target B2B manufacturers/factories, not retail stores.
- If data is missing, set it to null and include the field in `missing_fields`.

User input:
{raw_description}
{context_block}

Return only valid JSON matching the schema in the system prompt."""

    data: dict | None = None
    if settings.enable_tool_use_output:
        try:
            logger.info("Calling LLM with tool-use (model: %s)...", settings.model_balanced)
            tool_data = await call_llm_with_tools(
                prompt=prompt,
                tools=_requirements_tool_schema(),
                system_prompt=SYSTEM_PROMPT,
                model=settings.model_balanced,
                max_tokens=3500,
                temperature=0.0,
            )
            data = tool_data.get("parsed") if isinstance(tool_data.get("parsed"), dict) else tool_data
        except Exception:
            logger.warning("Tool-use parsing failed, falling back to JSON mode", exc_info=True)

    response_text = ""
    if data is None:
        # Use Sonnet (balanced) — regional strategy + clarifying questions need reasoning
        logger.info("Calling LLM (model: %s)...", settings.model_balanced)
        response_text = await call_llm_structured(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            model=settings.model_balanced,
            max_tokens=3000,
        )
    emit_progress("parsing", "structuring",
                  "Structuring product type, quantity, and quality requirements...",
                  progress_pct=50)
    if response_text:
        logger.info("Got LLM response (%d chars), parsing JSON...", len(response_text))

    # Parse JSON from response
    if data is None:
        try:
            # Handle potential markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(text)
            logger.info("✅ Parsed: product_type=%s, quantity=%s, %d search queries, %d regional searches, %d questions",
                         data.get("product_type"), data.get("quantity"),
                         len(data.get("search_queries", [])),
                         len(data.get("regional_searches", [])),
                         len(data.get("clarifying_questions", [])))
        except json.JSONDecodeError:
            logger.warning("JSON parse failed, trying regex fallback...")
            import re
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                logger.info("Regex fallback succeeded")
            else:
                logger.error("❌ Could not parse requirements from LLM response")
                return ParsedRequirements(
                    product_type="unknown",
                    missing_fields=["all_fields"],
                    search_queries=[raw_description + " manufacturer"],
                )

    if not isinstance(data, dict):
        data = {}

    product_type = data.get("product_type", "unknown")
    quantity = data.get("quantity")
    search_queries = data.get("search_queries", [])
    emit_progress("parsing", "product_identified",
                  f"Product type: {product_type}" +
                  (f", quantity: {quantity}" if quantity else "") +
                  f". Generated {len(search_queries)} search queries.",
                  progress_pct=75)

    data = _apply_domain_guardrails(raw_description, data)
    data = _enhance_clarifying_questions(data)

    # Emit progress about regional strategies found
    regional = data.get("regional_searches", [])
    questions = data.get("clarifying_questions", [])
    if regional:
        regions = [r.get("region", "?") for r in regional]
        emit_progress("parsing", "regional_strategy",
                      f"Identified {len(regional)} sourcing regions: {', '.join(regions)}")
    if questions:
        emit_progress("parsing", "clarifying",
                      f"Generated {len(questions)} clarifying questions for you")

    return ParsedRequirements(**data)
