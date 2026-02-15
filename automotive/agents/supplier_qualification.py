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

CRITICAL — understand the difference between these verification outcomes:
- "evidence_found" / "found" → Positive verification. Data confirms the claim.
- "not_found" → Search ran successfully but did NOT find evidence. This is a
  WEAK negative — the data may exist but not be indexed online.
- "data_unavailable" → The check COULD NOT RUN (API error, timeout, service
  not configured). This is NOT a negative result. It means we simply don't know.
  Treat this the same as "not checked."

Verdict rules:
- QUALIFIED: Positive verification evidence for hard criteria (IATF, financial,
  corporate), good capability match from website intelligence, no red flags.
- CONDITIONAL: Use this when verification data is UNAVAILABLE or INCOMPLETE.
  This is the CORRECT status when checks could not run, when IATF status is
  "data_unavailable", when financial data is "data_unavailable", or when only
  partial information could be gathered. Flag what needs manual verification.
  Also use for: IATF covers different scope, moderate financial risk, limited capacity.
- DISQUALIFIED: ONLY when there is CONFIRMED negative evidence — e.g. company
  is confirmed dissolved, confirmed fraudulent, or the supplier's demonstrated
  capabilities are a fundamental mismatch (e.g. they only do plastics and the
  requirement is for metal stamping).

Key principles:
- When verification data is unavailable, default to CONDITIONAL, never DISQUALIFIED.
- "data_unavailable" for IATF does NOT mean "no IATF certification" — it means
  we couldn't check. Mark as CONDITIONAL with a concern noting manual IATF
  verification is needed.
- "data_unavailable" for financial risk does NOT mean "high risk" — it means
  we have no data. This alone is never grounds for disqualification.
- A supplier discovered from credible sources (Thomasnet, industry directories)
  with relevant capabilities on their website deserves at least CONDITIONAL status.
- List specific items that need manual verification in the "concerns" field.

In your strengths, list what IS confirmed. In your concerns, list what NEEDS
manual verification and why.
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

    async def _empty_caps() -> dict:
        return {}

    website_task = (
        extract_supplier_capabilities(supplier.website)
        if supplier.website
        else _empty_caps()
    )

    results = await asyncio.gather(
        iatf_task, financial_task, corporate_task, reviews_task, website_task,
        return_exceptions=True,
    )

    iatf = results[0] if not isinstance(results[0], Exception) else {"status": "data_unavailable", "note": "Check threw exception"}
    financial = results[1] if not isinstance(results[1], Exception) else {"risk_level": "data_unavailable", "note": "Check threw exception"}
    corporate = results[2] if not isinstance(results[2], Exception) else {"status": "data_unavailable", "note": "Check threw exception"}
    reviews = results[3] if not isinstance(results[3], Exception) else {"rating": None, "review_count": 0, "note": "Check threw exception"}
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


def _explain_check_status(check_name: str, status: str, note: str = "") -> str:
    """Build a clear human-readable line explaining a verification check result."""
    if status in ("evidence_found", "found"):
        icon = "✓ VERIFIED"
    elif status == "not_found":
        icon = "⚠ NOT FOUND (search ran, no evidence found — may be indexed under different name)"
    elif status in ("data_unavailable", "check_failed", "not_checked", "unknown"):
        icon = "? DATA UNAVAILABLE (check could not run — this is NOT a negative result)"
    else:
        icon = f"  {status}"
    line = f"  {check_name}: {icon}"
    if note:
        line += f"\n    Note: {note}"
    return line


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

    # Build capabilities summary
    caps = supplier.capabilities
    caps_lines = []
    if caps.manufacturing_processes:
        caps_lines.append(f"  Processes: {', '.join(caps.manufacturing_processes)}")
    if caps.materials_processed:
        caps_lines.append(f"  Materials: {', '.join(caps.materials_processed)}")
    if caps.certifications_claimed:
        caps_lines.append(f"  Certifications claimed on website: {', '.join(caps.certifications_claimed)}")
    if caps.industries_served:
        caps_lines.append(f"  Industries: {', '.join(caps.industries_served)}")
    if caps.equipment_list:
        caps_lines.append(f"  Equipment: {', '.join(caps.equipment_list[:5])}")
    if caps.capacity_indicators:
        caps_lines.append(f"  Capacity: {', '.join(caps.capacity_indicators)}")
    if caps.company_description:
        caps_lines.append(f"  Description: {caps.company_description[:200]}")

    caps_text = "\n".join(caps_lines) if caps_lines else "  No website data available"

    user_msg = (
        f"=== SUPPLIER ===\n"
        f"Company: {supplier.company_name}\n"
        f"Location: {supplier.headquarters}\n\n"

        f"=== VERIFICATION RESULTS ===\n"
        f"(Remember: 'DATA UNAVAILABLE' means the check could NOT run — it is NOT a negative result)\n\n"
        f"{_explain_check_status('IATF 16949', supplier.iatf_status)}\n"
        f"{_explain_check_status('Financial Risk', supplier.financial_risk)}\n"
        f"{_explain_check_status('Corporate Registration', supplier.corporate_status)}\n"
        f"  Google Reviews: {supplier.google_rating or 'N/A'} ({supplier.review_count or 0} reviews)\n\n"

        f"=== WEBSITE INTELLIGENCE ===\n"
        f"{caps_text}\n\n"

        f"=== REQUIREMENT ===\n"
        f"Part: {requirement.part_description}\n"
        f"Process: {requirement.manufacturing_process}\n"
        f"Material: {requirement.material_family}\n"
        f"Certifications Required: {', '.join(requirement.certifications_required)}\n"
        f"Region Preference: {', '.join(requirement.preferred_regions)}\n"
        f"Volume: {requirement.annual_volume}/year\n\n"

        f"=== INSTRUCTIONS ===\n"
        f"If verification data is unavailable, use CONDITIONAL status and note what needs manual verification.\n"
        f"Only use DISQUALIFIED if there is CONFIRMED evidence of non-compliance or fundamental mismatch."
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
