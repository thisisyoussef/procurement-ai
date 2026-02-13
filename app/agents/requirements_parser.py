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
from app.core.llm_gateway import call_llm_structured
from app.core.progress import emit_progress
from app.schemas.agent_state import ParsedRequirements

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "requirements_parser.md").read_text()

EXAMPLE_INPUT = """I need 500 custom canvas tote bags, 14x16 inches, 12oz cotton canvas,
screen printed with my logo in 2 colors, delivered to LA by March 2026"""

EXAMPLE_OUTPUT = json.dumps({
    "product_type": "tote bag",
    "material": "12oz cotton canvas",
    "dimensions": "14x16 inches",
    "quantity": 500,
    "customization": "screen print, 2 colors, custom logo",
    "delivery_location": "Los Angeles, CA",
    "sourcing_preference": None,
    "deadline": "2026-03-01",
    "certifications_needed": [],
    "budget_range": None,
    "missing_fields": ["budget_range"],
    "search_queries": [
        "custom canvas tote bag manufacturer Los Angeles",
        "tote bag supplier wholesale USA",
        "cotton canvas tote bag factory custom printing",
        "12oz canvas bag maker screen printing",
        "promotional tote bag manufacturer California"
    ],
    "regional_searches": [
        {
            "region": "China",
            "language_code": "zh",
            "language_name": "Chinese",
            "search_queries": ["帆布手提袋生产厂家", "定制帆布袋工厂 丝印"],
            "rationale": "China is the largest producer of canvas bags with competitive pricing"
        },
        {
            "region": "India",
            "language_code": "hi",
            "language_name": "Hindi",
            "search_queries": ["कैनवास टोट बैग निर्माता", "कस्टम बैग फैक्ट्री"],
            "rationale": "India has strong cotton/canvas manufacturing with good quality at lower costs"
        }
    ],
    "clarifying_questions": [
        {
            "field": "budget_range",
            "question": "What's your target price per bag?",
            "importance": "recommended",
            "suggestions": ["Under $3/unit", "$3-8/unit", "$8-15/unit", "No budget constraint"]
        }
    ],
    "sourcing_strategy": "Canvas tote bags are best sourced from China (largest producer, most competitive pricing) and India (strong cotton manufacturing). US-based manufacturers can deliver faster but at higher cost."
})

EXAMPLE_INPUT_AUTOMOTIVE = """Need a North America supplier for stamped steel seat brackets,
300k units/year, IATF 16949, PPAP Level 3, tooling readiness in 16 weeks."""

EXAMPLE_OUTPUT_AUTOMOTIVE = json.dumps({
    "product_type": "stamped steel seat bracket",
    "material": "stamped steel",
    "dimensions": None,
    "quantity": 300000,
    "customization": "tooling readiness within 16 weeks",
    "delivery_location": None,
    "sourcing_preference": "North America",
    "deadline": None,
    "certifications_needed": ["IATF 16949", "PPAP Level 3"],
    "budget_range": None,
    "missing_fields": ["delivery_location", "budget_range"],
    "search_queries": [
        "stamped steel seat bracket manufacturer North America",
        "automotive seat bracket supplier IATF 16949 PPAP",
        "stamped steel automotive bracket factory tooling",
        "seat bracket OEM supplier Tier 1 Tier 2",
        "metal stamping supplier automotive seat components"
    ],
    "regional_searches": [
        {
            "region": "United States",
            "language_code": "en",
            "language_name": "English",
            "search_queries": ["automotive seat bracket stamping supplier", "IATF 16949 seat bracket manufacturer"],
            "rationale": "US suppliers offer strong APQP/PPAP process maturity and shorter launch support cycles"
        },
        {
            "region": "Mexico",
            "language_code": "es",
            "language_name": "Spanish",
            "search_queries": ["fabricante soporte asiento estampado automotriz", "proveedor automotriz IATF 16949 estampado"],
            "rationale": "Mexico has deep automotive metal stamping capacity and cost-efficient production"
        }
    ],
    "clarifying_questions": [
        {
            "field": "delivery_location",
            "question": "Which GM plant or delivery region should suppliers quote to?",
            "importance": "critical",
            "suggestions": ["Michigan, USA", "Ontario, Canada", "Mexico", "Multiple regions"]
        }
    ],
    "sourcing_strategy": "Prioritize automotive metal stampers with IATF and PPAP readiness in US/Mexico/Canada and verify tooling launch support."
})

EXAMPLE_LEAK_PRODUCT_TYPES = {
    "tote bag",
    "canvas tote bag",
    "custom canvas tote bag",
    "promotional tote bag",
}

AUTOMOTIVE_SIGNALS = {
    "automotive",
    "oem",
    "tier 1",
    "tier-1",
    "tier 2",
    "tier-2",
    "iatf",
    "ppap",
    "apqp",
    "stamped steel",
    "stamping",
    "seat bracket",
    "wire harness",
    "die cast",
    "forging",
    "drivetrain",
    "gm",
}


def _contains_any_signal(text: str, signals: set[str]) -> bool:
    haystack = text.lower()
    return any(signal in haystack for signal in signals)


def _looks_like_example_leak(raw_description: str, data: dict) -> bool:
    product_type = str(data.get("product_type") or "").strip().lower()
    query_blob = " ".join(data.get("search_queries") or []).lower()
    raw = raw_description.lower()

    if product_type in EXAMPLE_LEAK_PRODUCT_TYPES and "tote" not in raw and "bag" not in raw:
        return True
    if ("tote bag" in query_blob or "canvas tote" in query_blob) and "tote" not in raw:
        return True
    return False


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
        if candidate:
            return candidate
    return raw[:80]


def _apply_domain_guardrails(raw_description: str, data: dict) -> dict:
    raw = raw_description.lower()
    parsed_blob = " ".join(
        [
            str(data.get("product_type") or ""),
            str(data.get("material") or ""),
            str(data.get("customization") or ""),
            " ".join(data.get("search_queries") or []),
            " ".join(data.get("certifications_needed") or []),
        ]
    ).lower()
    automotive_mode = _contains_any_signal(raw, AUTOMOTIVE_SIGNALS) or _contains_any_signal(parsed_blob, AUTOMOTIVE_SIGNALS)

    if _looks_like_example_leak(raw_description, data):
        logger.warning("Detected parser example leakage; rebuilding product/search fields from raw input")
        data["product_type"] = _guess_product_type_from_raw(raw_description)
        data["search_queries"] = [
            f"{data['product_type']} manufacturer",
            f"{data['product_type']} supplier OEM",
            f"{data['product_type']} factory wholesale",
        ]

    if automotive_mode:
        product_type = str(data.get("product_type") or "").strip()
        if not product_type or product_type.lower() in EXAMPLE_LEAK_PRODUCT_TYPES:
            data["product_type"] = _guess_product_type_from_raw(raw_description)
        certifications = {c.strip() for c in (data.get("certifications_needed") or []) if c}
        if "iatf" in raw and not any("iatf" in c.lower() for c in certifications):
            certifications.add("IATF 16949")
        if "ppap" in raw and not any("ppap" in c.lower() for c in certifications):
            certifications.add("PPAP")
        data["certifications_needed"] = sorted(certifications)
        data["search_queries"] = [
            f"{data['product_type']} manufacturer automotive OEM",
            f"{data['product_type']} supplier IATF 16949 PPAP",
            f"{data['product_type']} factory Tier 1 Tier 2",
            f"{data['product_type']} tooling APQP launch supplier",
            f"{data['product_type']} North America supplier",
        ]
    return data


async def parse_requirements(raw_description: str) -> ParsedRequirements:
    """Parse a natural language product description into structured requirements.

    Uses Sonnet for enhanced reasoning — regional strategy, clarifying questions,
    and sourcing intelligence require stronger model capabilities.
    """
    logger.info("📋 Parsing requirements from: '%s'", raw_description[:100])
    emit_progress("parsing", "analyzing", "Analyzing your requirements...")

    prompt = f"""Use the examples only as schema/format guidance.
Do not copy example product categories, materials, or queries unless they are explicitly present in the user's input.

Here are examples:

Input: {EXAMPLE_INPUT}
Output: {EXAMPLE_OUTPUT}

Input: {EXAMPLE_INPUT_AUTOMOTIVE}
Output: {EXAMPLE_OUTPUT_AUTOMOTIVE}

Now parse this product description. Think strategically about the best sourcing regions and languages to search in.

Input: {raw_description}
Output:"""

    # Use Sonnet (balanced) — regional strategy + clarifying questions need reasoning
    logger.info("Calling LLM (model: %s)...", settings.model_balanced)
    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=3000,
    )
    logger.info("Got LLM response (%d chars), parsing JSON...", len(response_text))

    # Parse JSON from response
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

    data = _apply_domain_guardrails(raw_description, data)

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
