"""Agent G: Comparison — generates side-by-side supplier comparison."""

import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.schemas.agent_state import (
    ComparisonResult,
    DiscoveredSupplier,
    ParsedRequirements,
    SupplierComparison,
    VerificationResults,
)

settings = get_settings()
logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "comparison.md").read_text()


async def compare_suppliers(
    requirements: ParsedRequirements,
    suppliers: list[DiscoveredSupplier],
    verifications: VerificationResults,
) -> ComparisonResult:
    """
    Generate a side-by-side comparison of verified suppliers.

    Combines discovery data with verification scores to produce
    an actionable comparison for the user.
    """
    # Build supplier data with verification scores
    supplier_profiles = []
    verification_map = {v.supplier_name: v for v in verifications.verifications}

    for i, s in enumerate(suppliers):
        v = verification_map.get(s.name)
        profile = {
            "index": i,
            "name": s.name,
            "website": s.website,
            "product_page_url": s.product_page_url,
            "city": s.city,
            "country": s.country,
            "description": s.description,
            "categories": s.categories,
            "certifications": s.certifications,
            "google_rating": s.google_rating,
            "google_review_count": s.google_review_count,
            "source": s.source,
            "relevance_score": s.relevance_score,
            "estimated_shipping_cost": s.estimated_shipping_cost,
            "verification_score": v.composite_score if v else 0,
            "verification_risk": v.risk_level if v else "unknown",
            "verification_recommendation": v.recommendation if v else "unknown",
        }
        supplier_profiles.append(profile)

    # Only compare suppliers recommended for proceed or caution
    viable = [p for p in supplier_profiles if p["verification_recommendation"] != "reject"]
    if not viable:
        viable = supplier_profiles[:5]  # Fallback: show top 5 anyway

    logger.info("📊 Comparing %d suppliers (%d viable)", len(suppliers), len(viable))

    prompt = f"""Product requirements:
{requirements.model_dump_json(indent=2)}

Verified supplier profiles ({len(viable)} viable, showing top {min(len(viable), 15)}):
{json.dumps(viable[:15], indent=2, default=str)}

Compare these suppliers side by side. For each supplier, assess:
1. Estimated pricing capability (based on their profile, categories, location)
2. MOQ likelihood relative to buyer's quantity of {requirements.quantity or 'unknown'}
3. Estimated lead time
4. Certification match with buyer's needs: {requirements.certifications_needed}
5. Estimated shipping/freight cost to buyer's location: {requirements.delivery_location or 'unknown'}
6. Estimated landed cost (unit price + shipping per unit)
7. Strengths and weaknesses

For international suppliers, estimate shipping costs based on typical freight rates from their country to the buyer's delivery location. Consider product weight/volume category and common shipping methods (sea freight vs air freight).

Return JSON with this structure:
{{
  "comparisons": [
    {{
      "supplier_name": "...",
      "supplier_index": N,
      "verification_score": N,
      "estimated_unit_price": "$X-Y" or null,
      "estimated_shipping_cost": "$X-Y per unit" or "Standard domestic shipping" or null,
      "estimated_landed_cost": "$X-Y per unit (total)" or null,
      "moq": "estimated range" or null,
      "lead_time": "X-Y days" or null,
      "certifications": ["..."],
      "strengths": ["..."],
      "weaknesses": ["..."],
      "overall_score": 0-100,
      "price_score": 0.0-5.0,
      "quality_score": 0.0-5.0,
      "shipping_score": 0.0-5.0,
      "review_score": 0.0-5.0,
      "lead_time_score": 0.0-5.0
    }}
  ],
  "analysis_narrative": "2-3 paragraph analysis including shipping cost considerations...",
  "best_value": "supplier name",
  "best_quality": "supplier name",
  "best_speed": "supplier name"
}}"""

    # Cap at 15 suppliers to keep output within token limits
    capped = viable[:15]
    logger.info("Sending %d profiles to LLM for comparison...", len(capped))
    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=12000,
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
                logger.warning("Recovered comparison data from truncated JSON")
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
                return ComparisonResult(
                    comparisons=[],
                    analysis_narrative="Unable to generate comparison. Please try again.",
                )

    comparisons = []
    for c in data.get("comparisons", []):
        try:
            comparisons.append(SupplierComparison(
                supplier_name=c.get("supplier_name", "Unknown"),
                supplier_index=c.get("supplier_index", 0),
                verification_score=float(c.get("verification_score", 0)),
                estimated_unit_price=c.get("estimated_unit_price"),
                estimated_shipping_cost=c.get("estimated_shipping_cost"),
                estimated_landed_cost=c.get("estimated_landed_cost"),
                moq=c.get("moq"),
                lead_time=c.get("lead_time"),
                certifications=c.get("certifications", []),
                strengths=c.get("strengths", []),
                weaknesses=c.get("weaknesses", []),
                overall_score=float(c.get("overall_score", 0)),
                price_score=min(5, max(0, float(c.get("price_score", 0)))),
                quality_score=min(5, max(0, float(c.get("quality_score", 0)))),
                shipping_score=min(5, max(0, float(c.get("shipping_score", 0)))),
                review_score=min(5, max(0, float(c.get("review_score", 0)))),
                lead_time_score=min(5, max(0, float(c.get("lead_time_score", 0)))),
            ))
        except Exception:
            continue

    logger.info("✅ Comparison complete: %d compared | best_value=%s, best_quality=%s, best_speed=%s", len(comparisons), data.get("best_value"), data.get("best_quality"), data.get("best_speed"))
    return ComparisonResult(
        comparisons=comparisons,
        analysis_narrative=data.get("analysis_narrative", ""),
        best_value=data.get("best_value"),
        best_quality=data.get("best_quality"),
        best_speed=data.get("best_speed"),
    )
