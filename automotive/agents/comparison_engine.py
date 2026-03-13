"""Agent 4 — Comparison & Ranking Engine.

Normalizes all supplier intelligence into a weighted comparison matrix
with per-dimension scores and narratives.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from automotive.core.config import MODEL_TIER_BALANCED
from automotive.core.llm import call_llm_structured
from automotive.schemas.comparison import ComparisonMatrix, SupplierComparison
from automotive.schemas.qualification import QualificationResult, QualifiedSupplier
from automotive.schemas.requirements import ParsedRequirement

logger = logging.getLogger(__name__)

COMPARISON_SYSTEM_PROMPT = """\
You are Procurement AI's Comparison Engine for automotive procurement.

Given a list of qualified suppliers and the procurement requirement, produce
a comprehensive comparison matrix. For each supplier, score on these dimensions
(each 0–100):

1. Capability Fit (default 25%): Process match, material expertise, equipment,
   secondary operations, prototype capability.
2. Quality Profile (default 25%): IATF status, additional certs, quality system
   maturity from website analysis.
3. Geographic & Logistics (default 20%): Distance from buyer, USMCA compliance,
   logistics infrastructure.
4. Financial Stability (default 15%): Risk rating, revenue adequacy, years in business.
5. Scale & Capacity (default 10%): Employee count vs volume, facility indicators.
6. Market Reputation (default 5%): Google rating, review volume, industry presence.

For each supplier, also provide:
- A short narrative for each major dimension
- Unique strengths (2-3 bullet points)
- Notable risks (1-2 bullet points)
- Best fit scenario (one sentence)

Rank suppliers by weighted composite score. Provide a clear rationale
for the top recommendation.
"""


async def compare_suppliers(
    qualification_result: QualificationResult,
    requirement: ParsedRequirement,
    weight_profile: dict[str, float] | None = None,
) -> ComparisonMatrix:
    """Generate a full comparison matrix for qualified suppliers."""
    # Filter to qualified + conditional only
    eligible = [
        s for s in qualification_result.suppliers
        if s.qualification_status in ("qualified", "conditional")
    ]

    if not eligible:
        logger.warning("No eligible suppliers for comparison")
        return ComparisonMatrix(
            requirement_summary=requirement.part_description,
            comparison_date=datetime.now(timezone.utc).isoformat(),
        )

    weights = weight_profile or {
        "capability": 0.25, "quality": 0.25, "geography": 0.20,
        "financial": 0.15, "scale": 0.10, "reputation": 0.05,
    }

    # Build supplier summaries for LLM
    supplier_texts = []
    for s in eligible:
        supplier_texts.append(
            f"Supplier: {s.company_name}\n"
            f"  Location: {s.headquarters}\n"
            f"  IATF: {s.iatf_status} | Financial: {s.financial_risk} | Corporate: {s.corporate_status}\n"
            f"  Employees: {s.employee_count or 'unknown'} | Revenue: {s.estimated_revenue or 'unknown'}\n"
            f"  Google: {s.google_rating}/5 ({s.review_count} reviews)\n"
            f"  Processes: {', '.join(s.capabilities.manufacturing_processes)}\n"
            f"  Materials: {', '.join(s.capabilities.materials_processed)}\n"
            f"  Equipment: {', '.join(s.capabilities.equipment_list[:5])}\n"
            f"  Certs: {', '.join(s.capabilities.certifications_claimed)}\n"
            f"  Industries: {', '.join(s.capabilities.industries_served)}\n"
            f"  Status: {s.qualification_status}\n"
            f"  Strengths: {', '.join(s.strengths)}\n"
            f"  Concerns: {', '.join(s.concerns)}"
        )

    schema = {
        "type": "object",
        "properties": {
            "comparisons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "capability_score": {"type": "number"},
                        "quality_score": {"type": "number"},
                        "geographic_score": {"type": "number"},
                        "financial_score": {"type": "number"},
                        "scale_score": {"type": "number"},
                        "reputation_score": {"type": "number"},
                        "capability_narrative": {"type": "string"},
                        "quality_narrative": {"type": "string"},
                        "geographic_narrative": {"type": "string"},
                        "financial_narrative": {"type": "string"},
                        "unique_strengths": {"type": "array", "items": {"type": "string"}},
                        "notable_risks": {"type": "array", "items": {"type": "string"}},
                        "best_fit_for": {"type": "string"},
                    },
                    "required": ["company_name", "capability_score", "quality_score",
                                 "geographic_score", "financial_score", "scale_score",
                                 "reputation_score"],
                },
            },
            "top_recommendation": {"type": "string"},
            "recommendation_rationale": {"type": "string"},
        },
        "required": ["comparisons", "top_recommendation", "recommendation_rationale"],
    }

    user_msg = (
        f"Requirement: {requirement.part_description}\n"
        f"Category: {requirement.part_category} | Material: {requirement.material_family}\n"
        f"Volume: {requirement.annual_volume}/year | Certs: {', '.join(requirement.certifications_required)}\n"
        f"Regions: {', '.join(requirement.preferred_regions)}\n"
        f"Buyer plant: {requirement.buyer_plant_location or 'unspecified'}\n\n"
        f"Weights: {weights}\n\n"
        f"Suppliers to compare:\n\n" + "\n\n".join(supplier_texts)
    )

    try:
        result = await call_llm_structured(
            system=COMPARISON_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_BALANCED,
            max_tokens=8192,
        )
    except Exception:
        logger.exception("LLM comparison failed")
        result = {"comparisons": [], "top_recommendation": "", "recommendation_rationale": ""}

    # Build comparison entries
    comparisons = []
    name_to_supplier = {s.company_name.lower().strip(): s for s in eligible}

    for comp in result.get("comparisons", []):
        supplier = name_to_supplier.get(comp["company_name"].lower().strip())
        sid = supplier.supplier_id if supplier else ""

        composite = (
            weights["capability"] * comp.get("capability_score", 0)
            + weights["quality"] * comp.get("quality_score", 0)
            + weights["geography"] * comp.get("geographic_score", 0)
            + weights["financial"] * comp.get("financial_score", 0)
            + weights["scale"] * comp.get("scale_score", 0)
            + weights["reputation"] * comp.get("reputation_score", 0)
        )

        comparisons.append(SupplierComparison(
            supplier_id=sid,
            company_name=comp["company_name"],
            capability_score=comp.get("capability_score", 0),
            quality_score=comp.get("quality_score", 0),
            geographic_score=comp.get("geographic_score", 0),
            financial_score=comp.get("financial_score", 0),
            scale_score=comp.get("scale_score", 0),
            reputation_score=comp.get("reputation_score", 0),
            composite_score=round(composite, 1),
            capability_narrative=comp.get("capability_narrative", ""),
            quality_narrative=comp.get("quality_narrative", ""),
            geographic_narrative=comp.get("geographic_narrative", ""),
            financial_narrative=comp.get("financial_narrative", ""),
            unique_strengths=comp.get("unique_strengths", []),
            notable_risks=comp.get("notable_risks", []),
            best_fit_for=comp.get("best_fit_for", ""),
        ))

    comparisons.sort(key=lambda c: c.composite_score, reverse=True)
    ranking = [c.supplier_id for c in comparisons]

    return ComparisonMatrix(
        requirement_summary=requirement.part_description,
        comparison_date=datetime.now(timezone.utc).isoformat(),
        weight_profile=weights,
        suppliers=comparisons,
        overall_ranking=ranking,
        top_recommendation=result.get("top_recommendation", comparisons[0].company_name if comparisons else ""),
        recommendation_rationale=result.get("recommendation_rationale", ""),
    )


async def run(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point."""
    qual_data = state.get("qualification_result")
    req_data = state.get("parsed_requirement")
    if not qual_data or not req_data:
        return {"errors": [{"stage": "compare", "error": "Missing qualification_result or parsed_requirement"}]}

    qualification_result = QualificationResult(**qual_data)
    requirement = ParsedRequirement(**req_data)
    weight_profile = state.get("weight_profile")
    result = await compare_suppliers(qualification_result, requirement, weight_profile)

    return {
        "comparison_matrix": result.model_dump(),
        "current_stage": "compare",
        "messages": [{"role": "system", "content": f"Comparison complete: {len(result.suppliers)} suppliers ranked. Top: {result.top_recommendation}"}],
    }
