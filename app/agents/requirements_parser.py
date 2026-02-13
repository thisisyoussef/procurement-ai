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
GENERIC_QUERY_TERMS = {
    "manufacturer",
    "manufacturers",
    "factory",
    "factories",
    "supplier",
    "suppliers",
    "oem",
    "wholesale",
    "bulk",
    "custom",
    "production",
    "producer",
    "makers",
    "maker",
}
TOKEN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "need",
    "needs",
    "looking",
    "source",
    "find",
    "made",
    "make",
    "unit",
    "units",
    "piece",
    "pieces",
    "pcs",
    "per",
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


def _tokenize_non_generic(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.split(r"[^a-zA-Z0-9]+", text.lower()):
        cleaned = token.strip()
        if len(cleaned) < 3:
            continue
        if cleaned in TOKEN_STOPWORDS:
            continue
        tokens.add(cleaned)
    return tokens


def _looks_like_example_leak(raw_description: str, data: dict) -> bool:
    raw_tokens = _tokenize_non_generic(raw_description)
    if not raw_tokens:
        return False

    product_tokens = _tokenize_non_generic(str(data.get("product_type") or ""))
    query_tokens = _tokenize_non_generic(" ".join(data.get("search_queries") or []))
    query_tokens = {t for t in query_tokens if t not in GENERIC_QUERY_TERMS}

    if product_tokens and query_tokens and raw_tokens.isdisjoint(product_tokens) and raw_tokens.isdisjoint(query_tokens):
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
        data["search_queries"] = _build_default_search_queries(data["product_type"])

    product_type = str(data.get("product_type") or "").strip()
    if not product_type:
        data["product_type"] = _guess_product_type_from_raw(raw_description)
        product_type = str(data.get("product_type") or "").strip()
    if not data.get("search_queries"):
        data["search_queries"] = _build_default_search_queries(product_type)

    if automotive_mode:
        if not product_type:
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

    prompt = f"""Parse the sourcing request into structured JSON using ONLY this user input.

Hard rules:
- Do not use canned examples, defaults, or prior requests as product hints.
- Do not introduce product categories that are not implied by the input.
- Keep `product_type` tightly grounded in the user's wording.
- `search_queries` must target B2B manufacturers/factories, not retail stores.
- If data is missing, set it to null and include the field in `missing_fields`.

User input:
{raw_description}

Return only valid JSON matching the schema in the system prompt."""

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
