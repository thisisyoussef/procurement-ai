"""Agent 1 — Requirements Parser.

Transforms natural language procurement requests into structured
ParsedRequirement specifications using Claude Haiku.
"""

import logging
from typing import Any

from automotive.core.config import MODEL_TIER_CHEAP, TOOLING_ESTIMATES
from automotive.core.llm import call_llm_structured
from automotive.schemas.requirements import PARSED_REQUIREMENT_SCHEMA, ParsedRequirement

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are Tamkin's Requirements Parser — an expert automotive procurement analyst.
Your role is to convert natural language procurement requests into structured
specifications that will drive supplier discovery and RFQ generation.

You have deep knowledge of:
- Automotive manufacturing processes (stamping, casting, machining, molding,
  forging, PCBA assembly, wiring harness, rubber/sealing)
- Material specifications (steel grades like SPCC/HSLA/DP590, aluminum alloys
  like A380/A356/6061, engineering plastics like PA66-GF30/PBT/ABS)
- Quality standards (IATF 16949, ISO 9001, ISO 14001, PPAP levels 1-5, APQP)
- Trade compliance (USMCA rules of origin requiring 75% RVC, duty classifications)
- Industry norms (typical MOQs, tooling costs, lead times by part category)
- The tiered supply chain: Tier 1 (systems), Tier 2 (components), Tier 3 (basic
  parts), Tier 4 (raw materials), OEMs (apex buyers)

Rules:
1. Extract every explicit requirement from the buyer's message.
2. Infer implicit requirements based on automotive context:
   - If "automotive" context or OEM/Tier mentioned → IATF 16949 likely required
   - If volume > 10K/year → tooled production, not prototype
   - If "EV" or "electric vehicle" → consider thermal management, high-voltage
     isolation, and lightweight material requirements
   - If Mexico/USMCA mentioned → USMCA compliance is required
3. For any ambiguity, produce a "clarifications" entry with:
   - "question": The specific clarification question
   - "suggestions": 2-4 clickable quick-select answers the buyer can pick from.
     These should be realistic automotive industry options — NOT generic placeholders.
   - "suggested_default": What you'll assume if the buyer skips this question.
     Always provide a reasonable default so the pipeline can proceed.
   - "impact": One sentence on how this affects supplier matching.
   Also put the bare question text in "ambiguities" for backwards compatibility.
4. Never hallucinate specifications — if uncertain, flag as ambiguous.
5. Estimate market parameters (tooling cost range, lead time) based on the
   part category to set buyer expectations.
6. Classify complexity:
   - simple: single process, standard material, loose tolerances
   - moderate: 1-2 secondary ops, engineering material, standard tolerances
   - complex: multi-operation, specialty alloy, tight tolerances, complex geometry

Example clarification:
{
  "question": "What PPAP level is required for this program?",
  "suggestions": ["Level 3 (standard)", "Level 2 (reduced)", "Level 5 (full)", "Not required"],
  "suggested_default": "Level 3 (standard)",
  "impact": "PPAP level determines documentation requirements in the RFQ package"
}
"""


async def parse_requirements(raw_request: str) -> ParsedRequirement:
    """Parse a natural language procurement request into a structured specification."""
    logger.info("Parsing requirements from: %s...", raw_request[:100])

    result = await call_llm_structured(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_request}],
        output_schema=PARSED_REQUIREMENT_SCHEMA,
        model=MODEL_TIER_CHEAP,
        max_tokens=2048,
    )

    parsed = ParsedRequirement(**result)

    # Enrich with tooling estimates if not already set
    if not parsed.estimated_tooling_range and parsed.part_category in TOOLING_ESTIMATES:
        est = TOOLING_ESTIMATES[parsed.part_category]
        parsed.estimated_tooling_range = f"${est['low']:,}–${est['high']:,}"
        parsed.estimated_lead_time = f"{est['lead_weeks']} weeks tooling"

    logger.info(
        "Parsed: category=%s, material=%s, volume=%d, certs=%s, ambiguities=%d",
        parsed.part_category,
        parsed.material_family,
        parsed.annual_volume,
        parsed.certifications_required,
        len(parsed.ambiguities),
    )
    return parsed


async def run(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point."""
    raw_request = state.get("raw_request", "")
    if not raw_request:
        return {
            "errors": [{"stage": "parse", "error": "No raw_request provided"}],
            "current_stage": "parse",
        }

    parsed = await parse_requirements(raw_request)
    return {
        "parsed_requirement": parsed.model_dump(),
        "current_stage": "parse",
        "messages": [
            {
                "role": "system",
                "content": f"Requirements parsed: {parsed.part_category} / {parsed.material_family} / {parsed.annual_volume} units/yr",
            }
        ],
    }
