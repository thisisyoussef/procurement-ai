"""Agent G: Comparison — generates side-by-side supplier comparison."""

import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.core.progress import emit_progress
from app.schemas.agent_state import (
    ComparisonResult,
    DiscoveredSupplier,
    ParsedRequirements,
    SupplierComparison,
    VerificationResults,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Relevance gate ──────────────────────────────────────────────

_GENERIC_TERMS = {
    "manufacturer", "manufacturers", "factory", "factories", "supplier",
    "suppliers", "oem", "wholesale", "bulk", "custom", "production",
    "producer", "makers", "maker",
}
_STOPWORDS = {
    "the", "and", "for", "with", "from", "need", "needs", "looking",
    "source", "find", "made", "make", "unit", "units", "piece", "pieces",
    "pcs", "per",
}


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in re.split(r"[^a-zA-Z0-9]+", text.lower()):
        t = token.strip()
        if len(t) < 3 or t in _STOPWORDS or t in _GENERIC_TERMS:
            continue
        tokens.append(t)
    return tokens


def _relevance_gate(
    suppliers: list[DiscoveredSupplier],
    requirements: ParsedRequirements,
) -> list[DiscoveredSupplier]:
    """Second-pass relevance filter at comparison stage.

    Removes suppliers whose name + description have zero overlap with
    the core product-type terms. This catches cases where the LLM scorer
    in discovery gave a passing relevance_score despite the supplier being
    in a completely different industry.
    """
    anchors = _tokenize(requirements.product_type or "")
    if not anchors:
        return suppliers

    passed: list[DiscoveredSupplier] = []
    removed = 0
    for s in suppliers:
        blob = " ".join([
            s.name or "",
            s.description or "",
            " ".join(s.categories or []),
        ]).lower()
        hits = sum(1 for a in anchors if a in blob)
        min_required = 2 if len(anchors) >= 3 else 1
        if hits >= min_required:
            passed.append(s)
        else:
            removed += 1
            logger.info(
                "Relevance gate removed '%s' — no product-type anchor match "
                "(anchors=%s, supplier_text='%s')",
                s.name, anchors, blob[:120],
            )
    if removed:
        logger.info(
            "Relevance gate: removed %d/%d suppliers before comparison",
            removed, len(suppliers),
        )
    return passed
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "comparison.md").read_text()
HEAVY_FREIGHT_SIGNALS = {
    "tire",
    "rubber",
    "automotive",
    "machined",
    "metal",
    "steel",
    "aluminum",
    "copper",
    "chemical",
    "resin",
    "polymer",
    "industrial",
    "raw material",
    "compound",
    "molding",
    "injection",
}
HEAVY_FREIGHT_LOW_PER_UNIT_THRESHOLD_USD = 1.0
LOW_PER_UNIT_EXEMPTION_QTY = 20000
SHIPPING_GUARD_NOTE = (
    "Shipping estimate was flagged as low-confidence for heavy freight; "
    "lane-specific freight quote required."
)


def _is_heavy_freight_category(requirements: ParsedRequirements) -> bool:
    blob = " ".join(
        [
            requirements.product_type or "",
            requirements.material or "",
            requirements.customization or "",
            " ".join(requirements.certifications_needed or []),
        ]
    ).lower()
    return any(signal in blob for signal in HEAVY_FREIGHT_SIGNALS)


def _extract_min_usd_amount(text: str | None) -> float | None:
    if not text:
        return None
    normalized = text.lower().replace(",", "")
    matches = re.findall(r"\$?\s*(\d+(?:\.\d+)?)", normalized)
    if not matches:
        return None
    values: list[float] = []
    for raw in matches:
        try:
            values.append(float(raw))
        except ValueError:
            continue
    if not values:
        return None
    return min(values)


def _looks_like_per_unit_shipping(text: str | None) -> bool:
    if not text:
        return False
    normalized = text.lower()
    return any(token in normalized for token in {"per unit", "/unit", "unit equivalent", "per-piece", "per piece"})


def _apply_shipping_sanity_guard(
    comparison: SupplierComparison,
    requirements: ParsedRequirements,
) -> bool:
    if not _is_heavy_freight_category(requirements):
        return False
    if requirements.quantity and requirements.quantity >= LOW_PER_UNIT_EXEMPTION_QTY:
        return False
    if not _looks_like_per_unit_shipping(comparison.estimated_shipping_cost):
        return False

    min_usd = _extract_min_usd_amount(comparison.estimated_shipping_cost)
    if min_usd is None or min_usd >= HEAVY_FREIGHT_LOW_PER_UNIT_THRESHOLD_USD:
        return False

    comparison.estimated_shipping_cost = (
        "Freight quote required (heavy commodity). "
        "Per-unit equivalent is likely above $1.00 before final lane/mode assumptions."
    )
    if not any("freight quote" in weakness.lower() for weakness in comparison.weaknesses):
        comparison.weaknesses.append(SHIPPING_GUARD_NOTE)
    if comparison.estimated_landed_cost and "quote" not in comparison.estimated_landed_cost.lower():
        comparison.estimated_landed_cost = "Freight quote required to finalize landed cost"
    comparison.shipping_score = min(2.5, comparison.shipping_score)
    return True


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
    emit_progress("comparing", "relevance_gate",
                  f"Filtering {len(suppliers)} suppliers for product relevance...")

    # Second-pass relevance gate: remove off-category suppliers that slipped
    # through discovery scoring (e.g. tire companies when searching for gumballs)
    suppliers = _relevance_gate(suppliers, requirements)
    if not suppliers:
        logger.warning("Relevance gate removed ALL suppliers — returning empty comparison")
        return ComparisonResult(
            comparisons=[],
            analysis_narrative=(
                "No suppliers passed the relevance check for the requested product. "
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

    prompt = f"""Product requirements:
{requirements.model_dump_json(indent=2)}

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
                  f"Received scores for {len(data.get('comparisons', []))} suppliers. Applying shipping sanity checks...",
                  progress_pct=70)

    comparisons = []
    shipping_guard_adjustments = 0
    for c in data.get("comparisons", []):
        try:
            comparison_entry = SupplierComparison(
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
            )
            if _apply_shipping_sanity_guard(comparison_entry, requirements):
                shipping_guard_adjustments += 1
                logger.info(
                    "Shipping guard adjusted supplier '%s' due to low per-unit freight estimate.",
                    comparison_entry.supplier_name,
                )
            comparisons.append(comparison_entry)
        except Exception:
            continue

    logger.info("✅ Comparison complete: %d compared | best_value=%s, best_quality=%s, best_speed=%s", len(comparisons), data.get("best_value"), data.get("best_quality"), data.get("best_speed"))
    analysis_narrative = data.get("analysis_narrative", "")
    if shipping_guard_adjustments:
        guard_note = (
            f"Shipping numbers for {shipping_guard_adjustments} supplier(s) were converted to "
            "quote-required because automated per-unit freight looked unrealistically low for heavy freight."
        )
        analysis_narrative = f"{analysis_narrative}\n\n{guard_note}".strip()
    return ComparisonResult(
        comparisons=comparisons,
        analysis_narrative=analysis_narrative,
        best_value=data.get("best_value"),
        best_quality=data.get("best_quality"),
        best_speed=data.get("best_speed"),
    )
