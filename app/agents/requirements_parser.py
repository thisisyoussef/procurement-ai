"""Agent A: Requirements Parser — converts natural language to structured specs.

Enhanced to also generate:
- Regional search strategies with multilingual queries
- Clarifying questions for missing critical information
- Strategic sourcing approach narrative
"""

import json
import logging
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


async def parse_requirements(raw_description: str) -> ParsedRequirements:
    """Parse a natural language product description into structured requirements.

    Uses Sonnet for enhanced reasoning — regional strategy, clarifying questions,
    and sourcing intelligence require stronger model capabilities.
    """
    logger.info("📋 Parsing requirements from: '%s'", raw_description[:100])
    emit_progress("parsing", "analyzing", "Analyzing your requirements...")

    prompt = f"""Here is an example:

Input: {EXAMPLE_INPUT}
Output: {EXAMPLE_OUTPUT}

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
