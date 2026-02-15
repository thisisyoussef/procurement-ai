"""Agent H: Recommendation — synthesizes all data into ranked recommendations."""

import json
import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured, repair_truncated_json
from app.core.progress import emit_progress
from app.schemas.buyer_context import BuyerContext
from app.schemas.agent_state import (
    ComparisonResult,
    ParsedRequirements,
    RecommendationResult,
    SupplierComparison,
    SupplierRecommendation,
    SupplierVerification,
    VerificationResults,
)
from app.schemas.user_profile import UserSourcingProfile

settings = get_settings()
logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "recommendation.md").read_text()

PRIMARY_LANES = ("best_overall", "best_low_risk", "best_speed_to_order")
ALL_LANES = (*PRIMARY_LANES, "alternative")
LANE_ALIASES = {
    "best overall": "best_overall",
    "overall": "best_overall",
    "default": "best_overall",
    "best_overall": "best_overall",
    "best low risk": "best_low_risk",
    "best_low_risk": "best_low_risk",
    "low risk": "best_low_risk",
    "safest": "best_low_risk",
    "best speed to order": "best_speed_to_order",
    "best_speed_to_order": "best_speed_to_order",
    "best speed": "best_speed_to_order",
    "fastest": "best_speed_to_order",
    "speed": "best_speed_to_order",
    "alternative": "alternative",
    "alt": "alternative",
}
TECHNICAL_SIGNALS = {
    "pcb",
    "printed circuit",
    "electronic",
    "electronics",
    "semiconductor",
    "iso 13485",
    "medical device",
    "aerospace",
    "automotive",
    "iatf",
    "machined",
    "cnc",
    "precision",
    "injection molding",
    "stamped steel",
    "wire harness",
    "tolerance",
    "firmware",
    "custom tooling",
    "fr-4",
}


def _normalize_lane(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", " ").replace("_", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    canonical = LANE_ALIASES.get(normalized)
    if canonical in ALL_LANES:
        return canonical
    return None


def _coerce_confidence(value: str | None, overall_score: float) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    if overall_score >= 80:
        return "high"
    if overall_score >= 60:
        return "medium"
    return "low"


def _to_list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _parse_json_response(response_text: str) -> dict | None:
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_truncated_json(text)
        if repaired:
            try:
                logger.warning("Recovered recommendation data from truncated JSON")
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not json_match:
            return None
        repaired_match = repair_truncated_json(json_match.group())
        if not repaired_match:
            return None
        try:
            return json.loads(repaired_match)
        except json.JSONDecodeError:
            return None


def _lead_time_days(value: str | None) -> float:
    if not value:
        return 9999
    normalized = value.lower()
    range_match = re.search(r"(\d+)\s*-\s*(\d+)", normalized)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return (low + high) / 2
    single = re.search(r"(\d+)", normalized)
    if single:
        return float(single.group(1))
    return 9999


def _is_technical_category(requirements: ParsedRequirements) -> bool:
    blob = " ".join(
        [
            requirements.product_type or "",
            requirements.material or "",
            requirements.customization or "",
            " ".join(requirements.certifications_needed or []),
        ]
    ).lower()
    return any(signal in blob for signal in TECHNICAL_SIGNALS)


def _manual_verification_reason(requirements: ParsedRequirements) -> str:
    product = requirements.product_type or "this category"
    return (
        f"{product} often needs tighter technical validation before PO "
        "(spec tolerances, compliance docs, and pilot sample sign-off)."
    )


def _fallback_verify_checklist(technical: bool) -> list[str]:
    if technical:
        return [
            "Confirm latest compliance and test reports",
            "Approve production sample against specs",
            "Validate tooling, tolerances, and QC plan before PO",
        ]
    return []


def _comparison_maps(comparison: ComparisonResult) -> tuple[dict[int, SupplierComparison], dict[str, SupplierComparison]]:
    by_index: dict[int, SupplierComparison] = {}
    by_name: dict[str, SupplierComparison] = {}
    for row in comparison.comparisons:
        by_index[row.supplier_index] = row
        by_name[row.supplier_name.strip().lower()] = row
    return by_index, by_name


def _verification_maps(verifications: VerificationResults) -> tuple[dict[int, SupplierVerification], dict[str, SupplierVerification]]:
    by_index: dict[int, SupplierVerification] = {}
    by_name: dict[str, SupplierVerification] = {}
    for row in verifications.verifications:
        by_index[row.supplier_index] = row
        by_name[row.supplier_name.strip().lower()] = row
    return by_index, by_name


def _parse_recommendations(
    data: dict,
    comparison: ComparisonResult,
    verifications: VerificationResults,
) -> list[SupplierRecommendation]:
    comparison_by_index, comparison_by_name = _comparison_maps(comparison)
    verification_by_index, verification_by_name = _verification_maps(verifications)

    recommendations: list[SupplierRecommendation] = []
    seen_indices: set[int] = set()

    for raw in data.get("recommendations", []):
        if not isinstance(raw, dict):
            continue

        supplier_name = str(raw.get("supplier_name") or "").strip()
        supplier_index_raw = raw.get("supplier_index")

        supplier_index: int | None = None
        if isinstance(supplier_index_raw, int):
            supplier_index = supplier_index_raw
        elif isinstance(supplier_index_raw, float) and supplier_index_raw.is_integer():
            supplier_index = int(supplier_index_raw)
        elif supplier_name:
            comp = comparison_by_name.get(supplier_name.lower())
            if comp:
                supplier_index = comp.supplier_index

        if supplier_index is None:
            continue
        if supplier_index in seen_indices:
            continue

        comp = comparison_by_index.get(supplier_index)
        ver = verification_by_index.get(supplier_index) or verification_by_name.get(supplier_name.lower())

        overall_score = float(raw.get("overall_score", comp.overall_score if comp else 0))
        confidence = _coerce_confidence(raw.get("confidence"), overall_score)

        recommendation = SupplierRecommendation(
            rank=int(raw.get("rank", len(recommendations) + 1)),
            supplier_name=supplier_name or (comp.supplier_name if comp else "Unknown"),
            supplier_index=supplier_index,
            overall_score=overall_score,
            confidence=confidence,
            reasoning=str(raw.get("reasoning") or "").strip(),
            best_for=str(raw.get("best_for") or "").strip(),
            lane=_normalize_lane(raw.get("lane")),
            why_trust=_to_list_of_strings(raw.get("why_trust")),
            uncertainty_notes=_to_list_of_strings(raw.get("uncertainty_notes")),
            verify_before_po=_to_list_of_strings(raw.get("verify_before_po")),
            needs_manual_verification=bool(raw.get("needs_manual_verification", False)),
            manual_verification_reason=str(raw.get("manual_verification_reason") or "").strip() or None,
        )

        if not recommendation.reasoning:
            recommendation.reasoning = "Included based on comparison and verification fit."
        if not recommendation.best_for:
            recommendation.best_for = "viable option"
        if not recommendation.why_trust and ver:
            recommendation.why_trust = [f"Verification score {round(ver.composite_score)}/100 ({ver.risk_level} risk)."]
        if not recommendation.uncertainty_notes and ver and ver.recommendation != "proceed":
            recommendation.uncertainty_notes = [f"Verification outcome: {ver.recommendation}."]

        recommendations.append(recommendation)
        seen_indices.add(supplier_index)

    recommendations.sort(key=lambda rec: rec.rank)
    for idx, rec in enumerate(recommendations, start=1):
        rec.rank = idx
    return recommendations


def _apply_recommendation_floor(
    recommendations: list[SupplierRecommendation],
    comparison: ComparisonResult,
) -> tuple[list[SupplierRecommendation], str | None]:
    original_count = len(recommendations)
    viable_count = len(comparison.comparisons)
    if viable_count < 3 or len(recommendations) >= 3:
        return recommendations, None

    existing = {rec.supplier_index for rec in recommendations}
    sorted_comparison = sorted(
        comparison.comparisons,
        key=lambda row: row.overall_score,
        reverse=True,
    )
    for row in sorted_comparison:
        if row.supplier_index in existing:
            continue
        recommendations.append(
            SupplierRecommendation(
                rank=len(recommendations) + 1,
                supplier_name=row.supplier_name,
                supplier_index=row.supplier_index,
                overall_score=float(row.overall_score),
                confidence="medium" if row.overall_score >= 60 else "low",
                reasoning="Added by deterministic fallback from comparison ranking.",
                best_for="comparison fallback",
                lane=None,
                why_trust=[],
                uncertainty_notes=["Model output was incomplete for this candidate."],
                verify_before_po=[],
                needs_manual_verification=False,
                manual_verification_reason=None,
            )
        )
        existing.add(row.supplier_index)
        if len(recommendations) >= 3:
            break

    recommendations.sort(key=lambda rec: rec.rank)
    for idx, rec in enumerate(recommendations, start=1):
        rec.rank = idx

    rationale = (
        f"The model returned {original_count} recommendation(s) from {viable_count} viable suppliers. "
        "Fallback comparison ranking was used to preserve a minimum decision set."
    )
    return recommendations, rationale


def _pick_best_low_risk(
    recommendations: list[SupplierRecommendation],
    used_indices: set[int],
    verifications: VerificationResults,
) -> SupplierRecommendation | None:
    verification_by_index, _ = _verification_maps(verifications)
    risk_rank = {"low": 0, "medium": 1, "high": 2, "unknown": 3}
    candidates = [rec for rec in recommendations if rec.supplier_index not in used_indices]
    if not candidates:
        return None

    def _score(rec: SupplierRecommendation) -> tuple[int, float, int]:
        verification = verification_by_index.get(rec.supplier_index)
        risk = verification.risk_level if verification else "unknown"
        verification_score = verification.composite_score if verification else rec.overall_score
        return (risk_rank.get(risk, 3), -verification_score, rec.rank)

    candidates.sort(key=_score)
    return candidates[0]


def _pick_best_speed(
    recommendations: list[SupplierRecommendation],
    used_indices: set[int],
    comparison: ComparisonResult,
) -> SupplierRecommendation | None:
    comparison_by_index, _ = _comparison_maps(comparison)
    candidates = [rec for rec in recommendations if rec.supplier_index not in used_indices]
    if not candidates:
        return None

    candidates.sort(
        key=lambda rec: (
            _lead_time_days(comparison_by_index.get(rec.supplier_index).lead_time if comparison_by_index.get(rec.supplier_index) else None),
            -rec.overall_score,
            rec.rank,
        )
    )
    return candidates[0]


def _apply_lane_fallback(
    recommendations: list[SupplierRecommendation],
    comparison: ComparisonResult,
    verifications: VerificationResults,
) -> None:
    if not recommendations:
        return

    # Keep only the first assignment for each primary lane.
    seen_primary: set[str] = set()
    for rec in recommendations:
        rec.lane = _normalize_lane(rec.lane)
        if rec.lane in PRIMARY_LANES:
            if rec.lane in seen_primary:
                rec.lane = None
            else:
                seen_primary.add(rec.lane)

    used_indices = {rec.supplier_index for rec in recommendations if rec.lane in PRIMARY_LANES}

    if "best_overall" not in seen_primary:
        top = min(recommendations, key=lambda rec: rec.rank)
        top.lane = "best_overall"
        used_indices.add(top.supplier_index)
        seen_primary.add("best_overall")

    if "best_low_risk" not in seen_primary:
        low_risk = _pick_best_low_risk(recommendations, used_indices, verifications)
        if low_risk:
            low_risk.lane = "best_low_risk"
            used_indices.add(low_risk.supplier_index)
            seen_primary.add("best_low_risk")

    if "best_speed_to_order" not in seen_primary:
        fast = _pick_best_speed(recommendations, used_indices, comparison)
        if fast:
            fast.lane = "best_speed_to_order"
            used_indices.add(fast.supplier_index)
            seen_primary.add("best_speed_to_order")

    for rec in recommendations:
        if rec.lane not in ALL_LANES:
            rec.lane = "alternative"


def _apply_manual_verification_defaults(
    recommendations: list[SupplierRecommendation],
    requirements: ParsedRequirements,
) -> None:
    technical = _is_technical_category(requirements)
    if not technical:
        return

    reason = _manual_verification_reason(requirements)
    fallback_checklist = _fallback_verify_checklist(technical=True)
    for rec in recommendations:
        rec.needs_manual_verification = True
        if not rec.manual_verification_reason:
            rec.manual_verification_reason = reason
        if not rec.verify_before_po:
            rec.verify_before_po = fallback_checklist


def _lane_coverage(recommendations: list[SupplierRecommendation]) -> dict[str, int]:
    coverage = {lane: 0 for lane in ALL_LANES}
    for rec in recommendations:
        lane = _normalize_lane(rec.lane) or "alternative"
        coverage[lane] = coverage.get(lane, 0) + 1
    return coverage


def _build_checkpoint_summary(
    recommendations: list[SupplierRecommendation],
    lane_coverage: dict[str, int],
) -> str:
    if not recommendations:
        return "No recommendation candidates are ready yet. Review upstream comparison data and retry."

    top = recommendations[0]
    covered_primary = [lane for lane in PRIMARY_LANES if lane_coverage.get(lane, 0) > 0]
    if covered_primary:
        lanes = ", ".join(lane.replace("_", " ") for lane in covered_primary)
        return (
            f"Top pick: {top.supplier_name}. Decision lanes covered: {lanes}. "
            "Review trust notes and verification checklist before outreach."
        )
    return (
        f"Top pick: {top.supplier_name}. Lane coverage is limited, so review uncertainty notes before outreach."
    )


def _fallback_elimination_rationale(
    existing: str | None,
    recommendations: list[SupplierRecommendation],
    comparison: ComparisonResult,
    verifications: VerificationResults,
) -> str | None:
    if existing:
        return existing
    viable_count = len(comparison.comparisons)
    if viable_count and len(recommendations) < viable_count:
        rejected = len([v for v in verifications.verifications if v.recommendation == "reject"])
        return (
            f"Shortlist narrowed to {len(recommendations)} recommendation(s) from {viable_count} viable supplier(s). "
            f"Rejected suppliers in verification: {rejected}."
        )
    return None


async def generate_recommendation(
    requirements: ParsedRequirements,
    comparison: ComparisonResult,
    verifications: VerificationResults,
    buyer_context: BuyerContext | None = None,
    user_profile: UserSourcingProfile | None = None,
) -> RecommendationResult:
    """
    Generate final ranked supplier recommendations.

    Synthesizes all upstream data into actionable advice
    for a small business founder.
    """
    logger.info("🏆 Generating final recommendations...")
    emit_progress("recommending", "synthesizing",
                  f"Synthesizing data from {len(comparison.comparisons)} compared suppliers and "
                  f"{len(verifications.verifications)} verifications...")
    verification_summary = json.dumps(
        [
            {
                "name": v.supplier_name,
                "supplier_index": v.supplier_index,
                "score": v.composite_score,
                "risk": v.risk_level,
                "recommendation": v.recommendation,
                "summary": v.summary,
            }
            for v in verifications.verifications
        ],
        indent=2,
    )

    context_block = ""
    if buyer_context:
        context_block += f"\\nBuyer context:\\n{buyer_context.model_dump_json(indent=2)}\\n"
    if user_profile:
        context_block += f"\\nUser sourcing profile:\\n{user_profile.model_dump_json(indent=2)}\\n"

    prompt = f"""Product requirements:
{requirements.model_dump_json(indent=2)}
{context_block}

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
      "supplier_index": 2,
      "overall_score": 0-100,
      "confidence": "high|medium|low",
      "reasoning": "2-3 sentences",
      "best_for": "best overall | low risk | fastest delivery",
      "lane": "best_overall|best_low_risk|best_speed_to_order|alternative",
      "why_trust": ["compact evidence bullet"],
      "uncertainty_notes": ["compact uncertainty bullet"],
      "verify_before_po": ["manual check before PO"],
      "needs_manual_verification": true,
      "manual_verification_reason": "short reason"
    }}
  ],
  "executive_summary": "2-3 sentence overview",
  "narrative_briefing": "3-5 paragraph advisor-style recommendation briefing",
  "decision_checkpoint_summary": "short decision-readiness summary before outreach",
  "elimination_rationale": "plain-language note when shortlist is narrower than discovery breadth",
  "caveats": ["important warning 1", "important warning 2"]
}}

If viable suppliers are numerous, still output a representative ranked set (up to 12) and explain narrowing in elimination_rationale."""

    emit_progress("recommending", "ranking",
                  "AI is ranking suppliers and assigning decision lanes...",
                  progress_pct=30)
    logger.info("Sending comparison data to LLM for recommendation...")
    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=6144,
    )

    data = _parse_json_response(response_text)
    if data is None:
        return RecommendationResult(
            recommendations=[],
            executive_summary="Unable to generate recommendation. Insufficient data.",
            caveats=["Analysis could not be completed. Please try with more specific requirements."],
            decision_checkpoint_summary="Recommendation generation failed before decision checkpoint.",
            elimination_rationale="Model output could not be parsed.",
            lane_coverage={lane: 0 for lane in ALL_LANES},
        )

    recommendations = _parse_recommendations(data, comparison, verifications)
    emit_progress("recommending", "lane_assignment",
                  f"Parsed {len(recommendations)} recommendations. Assigning decision lanes...",
                  progress_pct=70)

    elimination_rationale = str(data.get("elimination_rationale") or "").strip() or None
    if settings.feature_focus_circle_search_v1:
        recommendations, floor_rationale = _apply_recommendation_floor(recommendations, comparison)
        if floor_rationale and not elimination_rationale:
            elimination_rationale = floor_rationale
        _apply_lane_fallback(recommendations, comparison, verifications)
        _apply_manual_verification_defaults(recommendations, requirements)

    coverage = _lane_coverage(recommendations)
    checkpoint = str(data.get("decision_checkpoint_summary") or "").strip()
    if not checkpoint:
        checkpoint = _build_checkpoint_summary(recommendations, coverage)

    elimination_rationale = _fallback_elimination_rationale(
        elimination_rationale,
        recommendations,
        comparison,
        verifications,
    )

    top_pick = recommendations[0].supplier_name if recommendations else "none"
    emit_progress("recommending", "complete",
                  f"Recommendations ready: {len(recommendations)} ranked suppliers. Top pick: {top_pick}.",
                  progress_pct=100)
    logger.info(
        "✅ Recommendation complete: %d recommendations, top pick: %s",
        len(recommendations), top_pick,
    )
    return RecommendationResult(
        recommendations=recommendations,
        executive_summary=str(data.get("executive_summary") or "").strip(),
        narrative_briefing=str(data.get("narrative_briefing") or "").strip(),
        caveats=_to_list_of_strings(data.get("caveats")),
        decision_checkpoint_summary=checkpoint,
        elimination_rationale=elimination_rationale,
        lane_coverage=coverage,
    )
