"""Agent G: Comparison — generates side-by-side supplier comparison."""

import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.core.progress import emit_progress
from app.schemas.buyer_context import BuyerContext
from app.schemas.agent_state import (
    ComparisonResult,
    DiscoveredSupplier,
    ParsedRequirements,
    SupplierComparison,
    VerificationResults,
)
from app.schemas.user_profile import UserSourcingProfile

settings = get_settings()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "comparison.md").read_text()

HEAVY_PRODUCT_HINTS = {
    "rubber",
    "tire",
    "tyre",
    "steel",
    "metal",
    "industrial",
    "machinery",
    "chemical",
    "resin",
    "bulk",
    "textile roll",
    "fabric roll",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}


def _parse_first_number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", value.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _to_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", str(value).replace(",", ""))
    return int(match.group(0)) if match else None


def _is_us_location(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.lower()
    if any(hint in normalized for hint in {"usa", "u.s.", "united states", ", us"}):
        return True
    state_match = re.search(r",\s*([A-Za-z]{2})(?:\b|$)", value)
    return bool(state_match and state_match.group(1).upper() in US_STATE_CODES)


def _apply_shipping_sanity_guard(
    requirements: ParsedRequirements,
    supplier_profile: dict,
    comparison_row: dict,
) -> tuple[dict, bool]:
    shipping_text = str(comparison_row.get("estimated_shipping_cost") or "")
    if "per unit" not in shipping_text.lower():
        return comparison_row, False

    min_shipping = _parse_first_number(shipping_text)
    if min_shipping is None or min_shipping > 1.0:
        return comparison_row, False

    supplier_country = str(supplier_profile.get("country") or "")
    supplier_is_us = supplier_country.lower() in {"us", "usa", "u.s.", "united states", "united states of america"}
    buyer_is_us = _is_us_location(requirements.delivery_location)
    is_international_lane = buyer_is_us and not supplier_is_us
    if not is_international_lane:
        return comparison_row, False

    quantity = _to_int(comparison_row.get("moq")) or requirements.quantity or 0
    if quantity >= 20000:
        return comparison_row, False

    heavy_text = " ".join(
        [
            str(requirements.product_type or ""),
            str(requirements.material or ""),
            " ".join(requirements.search_queries or []),
            str(supplier_profile.get("description") or ""),
            " ".join(supplier_profile.get("categories") or []),
        ]
    ).lower()
    if not any(hint in heavy_text for hint in HEAVY_PRODUCT_HINTS):
        return comparison_row, False

    normalized = dict(comparison_row)
    normalized["estimated_shipping_cost"] = "Freight quote required (auto-converted from low-confidence per-unit estimate)"
    normalized["estimated_landed_cost"] = "Freight quote required to finalize landed cost"
    weaknesses = normalized.get("weaknesses") or []
    if not any("freight" in str(w).lower() for w in weaknesses):
        weaknesses = [*weaknesses, "Freight quote required due to uncertain mode/weight assumptions."]
    normalized["weaknesses"] = weaknesses
    return normalized, True


async def compare_suppliers(
    requirements: ParsedRequirements,
    suppliers: list[DiscoveredSupplier],
    verifications: VerificationResults,
    buyer_context: BuyerContext | None = None,
    user_profile: UserSourcingProfile | None = None,
) -> ComparisonResult:
    """
    Generate a side-by-side comparison of verified suppliers.

    Combines discovery data with verification scores to produce
    an actionable comparison for the user.
    """
    emit_progress("comparing", "building_profiles",
                  f"Preparing {len(suppliers)} supplier profiles for comparison...")

    if not suppliers:
        logger.warning("No suppliers provided — returning empty comparison")
        return ComparisonResult(
            comparisons=[],
            analysis_narrative=(
                "No suppliers were available for comparison. "
                "The search may need to be re-run with more specific terms."
            ),
        )

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
    rejected_count = len([p for p in supplier_profiles if p["verification_recommendation"] == "reject"])
    if not viable:
        viable = supplier_profiles[:5]  # Fallback: show top 5 anyway

    emit_progress("comparing", "building_profiles",
                  f"Prepared {len(viable)} viable supplier profiles ({rejected_count} rejected)",
                  progress_pct=20)

    logger.info("📊 Comparing %d suppliers (%d viable, %d rejected)", len(suppliers), len(viable), rejected_count)

    context_block = ""
    if buyer_context:
        context_block += f"\nBuyer context:\n{buyer_context.model_dump_json(indent=2)}\n"
    if user_profile:
        context_block += f"\nUser sourcing profile:\n{user_profile.model_dump_json(indent=2)}\n"

    prompt = f"""Product requirements:
{requirements.model_dump_json(indent=2)}
{context_block}

Verified supplier profiles (total={len(supplier_profiles)}, viable={len(viable)}, rejected={rejected_count}, showing top {min(len(viable), 15)}):
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
If unit weight, density, or shipping mode is unclear for heavy industrial products, do NOT output tiny parcel-style per-unit shipping numbers. Use "Freight quote required" and explain assumptions in weaknesses.
If you output per-unit shipping, include assumptions in plain language (quantity and likely shipping mode).

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
}}

In analysis_narrative, if viable suppliers are much fewer than total suppliers, include one plain-language sentence explaining why the shortlist narrowed.
"""

    # Cap at 15 suppliers to keep output within token limits
    capped = viable[:15]
    supplier_names = [p["name"] for p in capped[:5]]
    emit_progress("comparing", "scoring",
                  f"AI is scoring {len(capped)} suppliers on price, quality, delivery, and reliability...",
                  progress_pct=35)
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

    emit_progress("comparing", "parsing_scores",
                  f"Received scores for {len(data.get('comparisons', []))} suppliers...",
                  progress_pct=70)

    comparisons = []
    converted_shipping_rows = 0
    for c in data.get("comparisons", []):
        try:
            supplier_index = int(c.get("supplier_index", 0))
            supplier_profile = supplier_profiles[supplier_index] if 0 <= supplier_index < len(supplier_profiles) else {}
            normalized_row, converted = _apply_shipping_sanity_guard(requirements, supplier_profile, c)
            if converted:
                converted_shipping_rows += 1
            comparison_entry = SupplierComparison(
                supplier_name=normalized_row.get("supplier_name", "Unknown"),
                supplier_index=normalized_row.get("supplier_index", 0),
                verification_score=float(normalized_row.get("verification_score", 0)),
                estimated_unit_price=normalized_row.get("estimated_unit_price"),
                estimated_shipping_cost=normalized_row.get("estimated_shipping_cost"),
                estimated_landed_cost=normalized_row.get("estimated_landed_cost"),
                moq=normalized_row.get("moq"),
                lead_time=normalized_row.get("lead_time"),
                certifications=normalized_row.get("certifications", []),
                strengths=normalized_row.get("strengths", []),
                weaknesses=normalized_row.get("weaknesses", []),
                overall_score=float(normalized_row.get("overall_score", 0)),
                price_score=min(5, max(0, float(normalized_row.get("price_score", 0)))),
                quality_score=min(5, max(0, float(normalized_row.get("quality_score", 0)))),
                shipping_score=min(5, max(0, float(normalized_row.get("shipping_score", 0)))),
                review_score=min(5, max(0, float(normalized_row.get("review_score", 0)))),
                lead_time_score=min(5, max(0, float(normalized_row.get("lead_time_score", 0)))),
            )
            comparisons.append(comparison_entry)
        except Exception:
            continue

    best_value = data.get("best_value", "")
    best_quality = data.get("best_quality", "")
    best_speed = data.get("best_speed", "")
    emit_progress("comparing", "complete",
                  f"Comparison complete: {len(comparisons)} suppliers scored. "
                  f"Best value: {best_value}. Best quality: {best_quality}.",
                  progress_pct=100)
    logger.info("✅ Comparison complete: %d compared | best_value=%s, best_quality=%s, best_speed=%s", len(comparisons), best_value, best_quality, best_speed)
    analysis_narrative = data.get("analysis_narrative", "")
    if converted_shipping_rows:
        analysis_narrative = (
            f"{analysis_narrative}\n\nShipping sanity guard: {converted_shipping_rows} estimate(s) "
            "converted to quote-required because per-unit freight looked unrealistically low for the trade lane."
        ).strip()

    return ComparisonResult(
        comparisons=comparisons,
        analysis_narrative=analysis_narrative,
        best_value=data.get("best_value"),
        best_quality=data.get("best_quality"),
        best_speed=data.get("best_speed"),
    )
