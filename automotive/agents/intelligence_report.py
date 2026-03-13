"""Agent 5 — Intelligence Report Generator.

Produces comprehensive per-supplier intelligence briefs using the
orchestrator-workers pattern for parallel report generation.
"""

import asyncio
import logging
from typing import Any

from automotive.core.config import MODEL_TIER_BALANCED
from automotive.core.llm import call_llm_structured
from automotive.schemas.comparison import ComparisonMatrix, SupplierComparison
from automotive.schemas.qualification import QualificationResult, QualifiedSupplier
from automotive.schemas.report import IntelligenceReport, IntelligenceReportResult, RiskAssessment
from automotive.schemas.requirements import ParsedRequirement

logger = logging.getLogger(__name__)

REPORT_SYSTEM_PROMPT = """\
You are Procurement AI's Intelligence Report Writer for automotive procurement.

Generate a comprehensive intelligence brief for the given supplier. The report
should give a procurement buyer everything they need to decide whether to
pursue this supplier. Write in a professional, analytical tone.

Report sections to produce:
1. Executive Summary (2-3 sentences): Who they are, why they fit, key differentiator.
2. Company Profile: Corporate details, ownership, facilities, key contacts.
3. Capability Assessment: Detailed analysis of manufacturing capabilities vs the
   specific requirement. Equipment, materials, capacity, secondary ops.
4. Quality Credentials: IATF 16949 details, ISO certs, quality maturity assessment.
5. Financial Health: Risk assessment, revenue adequacy, business stability.
6. Geographic Analysis: Distance, USMCA, logistics, regional labor context.
7. Competitive Positioning: Rank vs peers, unique strengths, optimal scenarios.

Also provide:
- Risk assessment entries (type, description, severity, mitigation)
- Recommended questions to ask this supplier
- Areas to probe during capability review
- RFQ focus areas specific to this supplier
"""


async def _generate_single_report(
    supplier: QualifiedSupplier,
    comparison: SupplierComparison | None,
    requirement: ParsedRequirement,
    peer_context: str,
) -> IntelligenceReport:
    """Generate an intelligence report for a single supplier."""
    schema = {
        "type": "object",
        "properties": {
            "executive_summary": {"type": "string"},
            "company_profile": {"type": "string"},
            "capability_assessment": {"type": "string"},
            "quality_credentials": {"type": "string"},
            "financial_health": {"type": "string"},
            "geographic_analysis": {"type": "string"},
            "competitive_positioning": {"type": "string"},
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk_type": {"type": "string"},
                        "description": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "mitigation": {"type": "string"},
                    },
                    "required": ["risk_type", "description", "severity", "mitigation"],
                },
            },
            "recommended_questions": {"type": "array", "items": {"type": "string"}},
            "areas_to_probe": {"type": "array", "items": {"type": "string"}},
            "rfq_focus_areas": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["executive_summary", "company_profile", "capability_assessment",
                      "quality_credentials", "financial_health", "geographic_analysis",
                      "competitive_positioning", "risks", "recommended_questions",
                      "areas_to_probe", "rfq_focus_areas"],
    }

    comp_text = ""
    if comparison:
        comp_text = (
            f"\nComparison scores: Capability={comparison.capability_score}, "
            f"Quality={comparison.quality_score}, Geographic={comparison.geographic_score}, "
            f"Financial={comparison.financial_score}, Scale={comparison.scale_score}, "
            f"Reputation={comparison.reputation_score}, Composite={comparison.composite_score}\n"
            f"Strengths: {', '.join(comparison.unique_strengths)}\n"
            f"Risks: {', '.join(comparison.notable_risks)}\n"
            f"Best fit for: {comparison.best_fit_for}"
        )

    user_msg = (
        f"Supplier: {supplier.company_name}\n"
        f"Location: {supplier.headquarters}\n"
        f"Website: {supplier.website or 'N/A'}\n"
        f"Phone: {supplier.phone or 'N/A'}\n"
        f"Email: {supplier.email or 'N/A'}\n"
        f"IATF: {supplier.iatf_status} (cert: {supplier.iatf_cert_number or 'N/A'})\n"
        f"Financial risk: {supplier.financial_risk}\n"
        f"Employees: {supplier.employee_count or 'unknown'}\n"
        f"Revenue: {supplier.estimated_revenue or 'unknown'}\n"
        f"Years in business: {supplier.years_in_business or 'unknown'}\n"
        f"Google rating: {supplier.google_rating} ({supplier.review_count} reviews)\n"
        f"Qualification: {supplier.qualification_status}\n"
        f"Capabilities: {supplier.capabilities.model_dump_json()}\n"
        f"{comp_text}\n\n"
        f"Requirement: {requirement.part_description}\n"
        f"Process: {requirement.manufacturing_process} | Material: {requirement.material_family}\n"
        f"Volume: {requirement.annual_volume}/year\n"
        f"Certs required: {', '.join(requirement.certifications_required)}\n"
        f"Regions: {', '.join(requirement.preferred_regions)}\n\n"
        f"Peer context (other suppliers on shortlist):\n{peer_context}"
    )

    try:
        result = await call_llm_structured(
            system=REPORT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_BALANCED,
            max_tokens=4096,
        )
    except Exception:
        logger.exception("Report generation failed for %s", supplier.company_name)
        result = {
            "executive_summary": f"Report generation failed for {supplier.company_name}. Manual review required.",
            "company_profile": "", "capability_assessment": "", "quality_credentials": "",
            "financial_health": "", "geographic_analysis": "", "competitive_positioning": "",
            "risks": [], "recommended_questions": [], "areas_to_probe": [], "rfq_focus_areas": [],
        }

    risks = [RiskAssessment(**r) for r in result.get("risks", [])]

    return IntelligenceReport(
        supplier_id=supplier.supplier_id,
        company_name=supplier.company_name,
        executive_summary=result.get("executive_summary", ""),
        company_profile=result.get("company_profile", ""),
        capability_assessment=result.get("capability_assessment", ""),
        quality_credentials=result.get("quality_credentials", ""),
        financial_health=result.get("financial_health", ""),
        geographic_analysis=result.get("geographic_analysis", ""),
        competitive_positioning=result.get("competitive_positioning", ""),
        risks=risks,
        recommended_questions=result.get("recommended_questions", []),
        areas_to_probe=result.get("areas_to_probe", []),
        rfq_focus_areas=result.get("rfq_focus_areas", []),
        contact_email=supplier.email or "",
        contact_phone=supplier.phone or "",
        website=supplier.website or "",
        address=supplier.headquarters,
    )


async def generate_reports(
    qualification_result: QualificationResult,
    comparison_matrix: ComparisonMatrix,
    requirement: ParsedRequirement,
) -> IntelligenceReportResult:
    """Generate intelligence reports for all qualified/conditional suppliers."""
    eligible = [
        s for s in qualification_result.suppliers
        if s.qualification_status in ("qualified", "conditional")
    ]

    if not eligible:
        return IntelligenceReportResult()

    # Build peer context
    peer_names = [s.company_name for s in eligible]
    peer_context = ", ".join(peer_names)

    # Map supplier IDs to comparison entries
    comp_map = {c.supplier_id: c for c in comparison_matrix.suppliers}

    # Generate reports in parallel (batched)
    reports = []
    batch_size = 3
    for i in range(0, len(eligible), batch_size):
        batch = eligible[i : i + batch_size]
        batch_reports = await asyncio.gather(
            *[
                _generate_single_report(s, comp_map.get(s.supplier_id), requirement, peer_context)
                for s in batch
            ],
            return_exceptions=True,
        )
        for r in batch_reports:
            if isinstance(r, Exception):
                logger.warning("Report generation failed: %s", r)
                continue
            reports.append(r)

    logger.info("Generated %d intelligence reports", len(reports))

    return IntelligenceReportResult(
        reports=reports,
        overall_market_summary=comparison_matrix.recommendation_rationale,
    )


async def run(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point."""
    qual_data = state.get("qualification_result")
    comp_data = state.get("comparison_matrix")
    req_data = state.get("parsed_requirement")

    if not qual_data or not comp_data or not req_data:
        return {"errors": [{"stage": "report", "error": "Missing required state data"}]}

    result = await generate_reports(
        QualificationResult(**qual_data),
        ComparisonMatrix(**comp_data),
        ParsedRequirement(**req_data),
    )

    return {
        "intelligence_reports": result.model_dump(),
        "current_stage": "report",
        "messages": [{"role": "system", "content": f"Generated {len(result.reports)} intelligence reports"}],
    }
