"""Agent H: Recommendation — synthesizes all data into ranked recommendations."""

import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.schemas.agent_state import (
    ComparisonResult,
    ParsedRequirements,
    RecommendationResult,
    SupplierRecommendation,
    VerificationResults,
)

settings = get_settings()
logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "recommendation.md").read_text()


async def generate_recommendation(
    requirements: ParsedRequirements,
    comparison: ComparisonResult,
    verifications: VerificationResults,
) -> RecommendationResult:
    """
    Generate final ranked supplier recommendations.

    Synthesizes all upstream data into actionable advice
    for a small business founder.
    """
    logger.info("🏆 Generating final recommendations...")
    verification_summary = json.dumps([
        {
            "name": v.supplier_name,
            "score": v.composite_score,
            "risk": v.risk_level,
            "recommendation": v.recommendation,
            "summary": v.summary,
        }
        for v in verifications.verifications
    ], indent=2)

    prompt = f"""Product requirements:
{requirements.model_dump_json(indent=2)}

Supplier comparison results:
{comparison.model_dump_json(indent=2)}

Verification summary:
{verification_summary}

Based on ALL of the above data, provide your final recommendation.

Return JSON:
{{
  "recommendations": [
    {{
      "rank": 1,
      "supplier_name": "...",
      "supplier_index": N,
      "overall_score": 0-100,
      "confidence": "high|medium|low",
      "reasoning": "2-3 sentences",
      "best_for": "best overall | budget pick | fastest delivery | highest quality"
    }}
  ],
  "executive_summary": "2-3 sentence overview",
  "caveats": ["important warning 1", "important warning 2"]
}}

Include ALL viable suppliers (up to 12 recommendations). Consider total landed cost (unit price + shipping), not just unit price. Be direct and actionable."""

    logger.info("Sending comparison data to LLM for recommendation...")
    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=6144,
    )

    try:
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try repairing truncated JSON (common when LLM hits max_tokens)
        from app.core.llm_gateway import repair_truncated_json
        repaired = repair_truncated_json(text)
        data = None
        if repaired:
            try:
                data = json.loads(repaired)
                logger.warning("Recovered recommendation data from truncated JSON")
            except json.JSONDecodeError:
                pass
        if data is None:
            import re
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                repaired2 = repair_truncated_json(json_match.group())
                try:
                    data = json.loads(repaired2) if repaired2 else None
                except json.JSONDecodeError:
                    data = None
            if data is None:
                return RecommendationResult(
                    recommendations=[],
                    executive_summary="Unable to generate recommendation. Insufficient data.",
                    caveats=["Analysis could not be completed. Please try with more specific requirements."],
                )

    recommendations = []
    for r in data.get("recommendations", []):
        try:
            recommendations.append(SupplierRecommendation(
                rank=int(r.get("rank", len(recommendations) + 1)),
                supplier_name=r.get("supplier_name", "Unknown"),
                supplier_index=r.get("supplier_index", 0),
                overall_score=float(r.get("overall_score", 0)),
                confidence=r.get("confidence", "low"),
                reasoning=r.get("reasoning", ""),
                best_for=r.get("best_for", ""),
            ))
        except Exception:
            continue

    logger.info("✅ Recommendation complete: %d recommendations, top pick: %s", len(recommendations), recommendations[0].supplier_name if recommendations else "none")
    return RecommendationResult(
        recommendations=recommendations,
        executive_summary=data.get("executive_summary", ""),
        caveats=data.get("caveats", []),
    )
