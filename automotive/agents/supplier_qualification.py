"""Agent 3 — Supplier Qualification & Verification.

Runs parallel verification checks (IATF, D&B, OpenCorporates, website, reviews)
on each discovered supplier and renders a qualification verdict.
"""

import asyncio
import logging
from typing import Any

from automotive.core.config import MODEL_TIER_BALANCED
from automotive.core.llm import call_llm_structured
from automotive.schemas.discovery import DiscoveredSupplier, DiscoveryResult
from automotive.schemas.qualification import (
    QualificationResult,
    QualifiedSupplier,
    WebsiteCapabilities,
)
from automotive.schemas.requirements import ParsedRequirement
from automotive.tools.firecrawl_search import extract_supplier_capabilities
from automotive.tools.verification import (
    check_corporate_registration,
    check_financial_health_dnb,
    check_google_reviews,
    check_iatf_certification,
)

logger = logging.getLogger(__name__)

QUALIFICATION_SYSTEM_PROMPT = """\
You are Tamkin's Supplier Qualification Agent for automotive procurement.

Given the verification data collected for a supplier, render a qualification verdict.

Use the think tool approach — before deciding, list:
1. The specific qualification criteria for this procurement
2. How each criterion maps to the collected data
3. Any gaps in the data
4. Your verdict with rationale

Verdict rules:
- QUALIFIED: All hard criteria met (active IATF 16949 if required, acceptable
  financial risk, confirmed registration), capability match >= 70%, no
  disqualifying flags.
- CONDITIONAL: Most criteria met but with noted gaps (IATF covers different
  scope, moderate financial risk, limited capacity). Flagged for buyer review.
- DISQUALIFIED: Hard criteria failed (no IATF 16949 when required, high
  financial risk, company dissolved, fundamental capability mismatch).

Never qualify a supplier without verified IATF 16949 when IATF is required.
Never disqualify solely based on missing soft criteria.
"""


async def _verify_single_supplier(
    supplier: DiscoveredSupplier,
    requirement: ParsedRequirement,
) -> QualifiedSupplier:
    """Run all verification checks for one supplier in parallel."""
    # Run all checks concurrently
    iatf_task = check_iatf_certification(supplier.company_name, supplier.headquarters)
    financial_task = check_financial_health_dnb(supplier.company_name)
    corporate_task = check_corporate_registration(supplier.company_name)
    reviews_task = check_google_reviews(supplier.company_name, supplier.headquarters)

    website_task = (
        extract_supplier_capabilities(supplier.website)
        if supplier.website
        else asyncio.coroutine(lambda: {})()
    )

    results = await asyncio.gather(
        iatf_task, financial_task, corporate_task, reviews_task, website_task,
        return_exceptions=True,
    )

    iatf = results[0] if not isinstance(results[0], Exception) else {"status": "check_failed"}
    financial = results[1] if not isinstance(results[1], Exception) else {"risk_level": "unknown"}
    corporate = results[2] if not isinstance(results[2], Exception) else {"status": "check_failed"}
    reviews = results[3] if not isinstance(results[3], Exception) else {"rating": None, "review_count": 0}
    website_caps = results[4] if not isinstance(results[4], Exception) else {}

    capabilities = WebsiteCapabilities(**website_caps) if isinstance(website_caps, dict) and website_caps else WebsiteCapabilities()

    # Build the qualified supplier record
    qualified = QualifiedSupplier(
        supplier_id=supplier.supplier_id,
        company_name=supplier.company_name,
        qualification_status="pending",
        iatf_status=iatf.get("status", "unknown"),
        iatf_cert_number=iatf.get("cert_number"),
        iatf_scope=iatf.get("scope"),
        iatf_expiry=iatf.get("expiry"),
        financial_risk=financial.get("risk_level", "unknown"),
        duns_number=financial.get("duns_number"),
        paydex_score=financial.get("paydex_score"),
        estimated_revenue=financial.get("estimated_revenue") or supplier.estimated_revenue,
        employee_count=financial.get("employee_count") or supplier.employee_count,
        years_in_business=financial.get("years_in_business"),
        corporate_status=corporate.get("status", "unknown"),
        capabilities=capabilities,
        reputation_score=min(100, (reviews.get("rating", 0) or 0) * 20),
        google_rating=reviews.get("rating"),
        review_count=reviews.get("review_count", 0),
        website=supplier.website,
        headquarters=supplier.headquarters,
        manufacturing_locations=supplier.manufacturing_locations,
        phone=supplier.phone,
        email=supplier.email,
        sources=supplier.sources,
    )

    return qualified


async def _render_verdict(
    supplier: QualifiedSupplier,
    requirement: ParsedRequirement,
) -> QualifiedSupplier:
    """Use LLM to render the final qualification verdict."""
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["qualified", "conditional", "disqualified"]},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "concerns": {"type": "array", "items": {"type": "string"}},
            "disqualification_reason": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["status", "strengths", "concerns", "confidence"],
    }

    user_msg = (
        f"Supplier: {supplier.company_name}\n"
        f"Location: {supplier.headquarters}\n"
        f"IATF Status: {supplier.iatf_status}\n"
        f"Financial Risk: {supplier.financial_risk}\n"
        f"Corporate Status: {supplier.corporate_status}\n"
        f"Google Rating: {supplier.google_rating} ({supplier.review_count} reviews)\n"
        f"Capabilities: {supplier.capabilities.model_dump_json()}\n\n"
        f"Requirement:\n"
        f"Part: {requirement.part_description}\n"
        f"Process: {requirement.manufacturing_process}\n"
        f"Material: {requirement.material_family}\n"
        f"Certifications Required: {', '.join(requirement.certifications_required)}\n"
        f"Region Preference: {', '.join(requirement.preferred_regions)}\n"
        f"Volume: {requirement.annual_volume}/year"
    )

    try:
        result = await call_llm_structured(
            system=QUALIFICATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_BALANCED,
            max_tokens=1024,
        )
        supplier.qualification_status = result.get("status", "conditional")
        supplier.strengths = result.get("strengths", [])
        supplier.concerns = result.get("concerns", [])
        supplier.disqualification_reason = result.get("disqualification_reason")
        supplier.overall_confidence = result.get("confidence", 0.5)
    except Exception:
        logger.exception("Verdict rendering failed for %s", supplier.company_name)
        supplier.qualification_status = "conditional"
        supplier.concerns = ["Automated qualification assessment failed — manual review required"]
        supplier.overall_confidence = 0.3

    return supplier


async def qualify_suppliers(
    discovery_result: DiscoveryResult,
    requirement: ParsedRequirement,
) -> QualificationResult:
    """Run qualification pipeline on all discovered suppliers."""
    logger.info("Starting qualification for %d suppliers", len(discovery_result.suppliers))

    # Verify all suppliers in parallel (batched to avoid API rate limits)
    batch_size = 5
    qualified_suppliers = []

    for i in range(0, len(discovery_result.suppliers), batch_size):
        batch = discovery_result.suppliers[i : i + batch_size]
        verified = await asyncio.gather(
            *[_verify_single_supplier(s, requirement) for s in batch],
            return_exceptions=True,
        )
        for result in verified:
            if isinstance(result, Exception):
                logger.warning("Verification failed: %s", result)
                continue
            qualified_suppliers.append(result)

    # Render verdicts in parallel
    with_verdicts = await asyncio.gather(
        *[_render_verdict(s, requirement) for s in qualified_suppliers],
        return_exceptions=True,
    )
    final_suppliers = [s for s in with_verdicts if not isinstance(s, Exception)]

    q_count = sum(1 for s in final_suppliers if s.qualification_status == "qualified")
    c_count = sum(1 for s in final_suppliers if s.qualification_status == "conditional")
    d_count = sum(1 for s in final_suppliers if s.qualification_status == "disqualified")

    logger.info("Qualification complete: %d qualified, %d conditional, %d disqualified", q_count, c_count, d_count)

    return QualificationResult(
        qualified_count=q_count,
        conditional_count=c_count,
        disqualified_count=d_count,
        suppliers=final_suppliers,
        verification_summary=f"{q_count} qualified, {c_count} conditional, {d_count} disqualified out of {len(final_suppliers)} checked",
    )


async def run(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point."""
    disc_data = state.get("discovery_result")
    req_data = state.get("parsed_requirement")
    if not disc_data or not req_data:
        return {"errors": [{"stage": "qualify", "error": "Missing discovery_result or parsed_requirement"}]}

    discovery_result = DiscoveryResult(**disc_data)
    requirement = ParsedRequirement(**req_data)
    result = await qualify_suppliers(discovery_result, requirement)

    return {
        "qualification_result": result.model_dump(),
        "current_stage": "qualify",
        "messages": [{"role": "system", "content": f"Qualification: {result.verification_summary}"}],
    }
