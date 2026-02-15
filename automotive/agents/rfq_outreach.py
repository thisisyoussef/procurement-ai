"""Agent 6 — RFQ Preparation & Outreach.

Generates professional RFQ packages and manages email outreach via Resend.
All emails require explicit human approval before sending.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from automotive.core.config import MODEL_TIER_BALANCED
from automotive.core.llm import call_llm_structured
from automotive.schemas.qualification import QualifiedSupplier, QualificationResult
from automotive.schemas.report import IntelligenceReport, IntelligenceReportResult
from automotive.schemas.requirements import ParsedRequirement
from automotive.schemas.rfq import (
    DeliverySchedule,
    OutreachRecord,
    PackagingRequirements,
    QualityRequirements,
    RFQLineItem,
    RFQPackage,
    RFQResult,
    ToolingTerms,
)

logger = logging.getLogger(__name__)

RFQ_SYSTEM_PROMPT = """\
You are Tamkin's RFQ Writer for automotive procurement.

Generate a professional, concise RFQ email that:
1. Opens with the buyer's company name and a brief context
2. References the supplier's specific capability that makes them a fit
3. Lists key specifications clearly
4. States the response deadline
5. Lists attachments
6. Provides clear response instructions
7. Closes professionally

Keep the email under 300 words. Use a professional but approachable tone.
Do not use jargon without explanation. The subject line must be under 60 characters.
"""


async def generate_rfq_package(
    requirement: ParsedRequirement,
    qualification_result: QualificationResult,
    intelligence_reports: IntelligenceReportResult,
    buyer_company: str = "",
    buyer_contact_name: str = "",
    buyer_contact_email: str = "",
) -> RFQResult:
    """Generate RFQ packages for all qualified suppliers."""
    eligible = [
        s for s in qualification_result.suppliers
        if s.qualification_status in ("qualified", "conditional")
    ]

    if not eligible:
        return RFQResult()

    rfq_id = f"RFQ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    deadline = (datetime.now(timezone.utc) + timedelta(weeks=2)).strftime("%B %d, %Y")

    # Build the base RFQ package
    line_item = RFQLineItem(
        description=requirement.part_description,
        material_spec=requirement.material_spec or requirement.material_family,
        process_type=requirement.manufacturing_process,
        annual_volume=requirement.annual_volume,
        lot_size=requirement.lot_size or 0,
    )

    quality_block = QualityRequirements(
        iatf_16949_required="IATF 16949" in requirement.certifications_required,
        ppap_level=requirement.ppap_level or "3",
    )

    rfq_package = RFQPackage(
        rfq_id=rfq_id,
        rfq_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        response_deadline=deadline,
        buyer_company=buyer_company,
        buyer_contact_name=buyer_contact_name,
        buyer_contact_email=buyer_contact_email,
        line_items=[line_item],
        quality_block=quality_block,
        delivery_schedule=DeliverySchedule(
            delivery_frequency="Per production schedule",
            shipping_terms="FOB Origin",
        ),
        packaging_requirements=PackagingRequirements(),
        tooling_terms=ToolingTerms(),
    )

    # Generate personalized emails for each supplier
    report_map = {r.supplier_id: r for r in intelligence_reports.reports}
    outreach_records = []

    for supplier in eligible:
        report = report_map.get(supplier.supplier_id)
        email_content = await _generate_email(
            supplier, requirement, rfq_package, report, buyer_company, buyer_contact_name,
        )

        outreach_records.append(OutreachRecord(
            supplier_id=supplier.supplier_id,
            supplier_name=supplier.company_name,
            recipient_email=supplier.email or "",
            delivery_status="draft",
        ))

        # Store personalized email on the package (for the first/template)
        if not rfq_package.email_subject:
            rfq_package.email_subject = email_content.get("subject", "")
            rfq_package.email_body = email_content.get("body", "")

    logger.info("Generated RFQ package %s for %d suppliers", rfq_id, len(outreach_records))

    return RFQResult(
        rfq_package=rfq_package,
        outreach_records=outreach_records,
        total_sent=0,
        total_bounced=0,
    )


async def _generate_email(
    supplier: QualifiedSupplier,
    requirement: ParsedRequirement,
    rfq: RFQPackage,
    report: IntelligenceReport | None,
    buyer_company: str,
    buyer_name: str,
) -> dict[str, str]:
    """Generate a personalized RFQ email for a specific supplier."""
    schema = {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["subject", "body"],
    }

    relevant_capability = ""
    if report and report.capability_assessment:
        relevant_capability = report.capability_assessment[:200]
    elif supplier.capabilities.manufacturing_processes:
        relevant_capability = ", ".join(supplier.capabilities.manufacturing_processes[:3])

    user_msg = (
        f"Generate an RFQ email for:\n"
        f"Supplier: {supplier.company_name}\n"
        f"Contact: {supplier.email or 'sales@' + (supplier.website or 'company.com').replace('https://', '').replace('http://', '').split('/')[0]}\n"
        f"Relevant capability: {relevant_capability}\n\n"
        f"RFQ Details:\n"
        f"Buyer: {buyer_company} ({buyer_name})\n"
        f"Part: {requirement.part_description}\n"
        f"Material: {requirement.material_spec or requirement.material_family}\n"
        f"Process: {requirement.manufacturing_process}\n"
        f"Volume: {requirement.annual_volume}/year in lots of {requirement.lot_size or 'TBD'}\n"
        f"Certs: {', '.join(requirement.certifications_required)}\n"
        f"PPAP Level: {requirement.ppap_level or '3'}\n"
        f"Deadline: {rfq.response_deadline}\n\n"
        f"Attachments to mention: Technical specification PDF, Quote response template Excel"
    )

    try:
        result = await call_llm_structured(
            system=RFQ_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_BALANCED,
            max_tokens=1024,
        )
        return result
    except Exception:
        logger.exception("Email generation failed for %s", supplier.company_name)
        return {
            "subject": f"RFQ: {buyer_company} – {requirement.part_description}",
            "body": f"Dear {supplier.company_name},\n\nPlease find attached our RFQ for {requirement.part_description}.\n\nPlease respond by {rfq.response_deadline}.\n\nRegards,\n{buyer_name}",
        }


async def send_rfqs(rfq_result: RFQResult) -> RFQResult:
    """Send approved RFQs via Resend. Only called after human approval."""
    from app.core.config import get_settings

    settings = get_settings()

    # Mark all draft records as approved (gate already gave approval)
    for record in rfq_result.outreach_records:
        if record.delivery_status == "draft":
            record.delivery_status = "approved"

    if not settings.resend_api_key:
        logger.warning("Resend not configured — RFQs marked as approved but not sent. "
                       "Configure RESEND_API_KEY to enable email delivery.")
        rfq_result.total_sent = 0
        return rfq_result

    import resend

    resend.api_key = settings.resend_api_key
    sent_count = 0
    bounced_count = 0

    for record in rfq_result.outreach_records:
        if not record.recipient_email or record.delivery_status != "approved":
            continue

        try:
            resend.Emails.send({
                "from": settings.from_email,
                "to": [record.recipient_email],
                "subject": rfq_result.rfq_package.email_subject,
                "html": rfq_result.rfq_package.email_body.replace("\n", "<br>"),
            })
            record.delivery_status = "sent"
            record.sent_at = datetime.now(timezone.utc).isoformat()
            sent_count += 1
        except Exception:
            logger.exception("Failed to send RFQ to %s", record.recipient_email)
            record.delivery_status = "failed"
            bounced_count += 1

    rfq_result.total_sent = sent_count
    rfq_result.total_bounced = bounced_count
    logger.info("Sent %d RFQs, %d failed", sent_count, bounced_count)

    return rfq_result


async def run_send(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point — sends RFQs after human approval."""
    rfq_data = state.get("rfq_result")
    if not rfq_data:
        return {"errors": [{"stage": "rfq_send", "error": "No RFQ data to send"}]}

    rfq_result = RFQResult(**rfq_data)
    result = await send_rfqs(rfq_result)

    return {
        "rfq_result": result.model_dump(),
        "messages": [{"role": "system", "content": f"RFQ emails: {result.total_sent} sent, {result.total_bounced} bounced"}],
    }


async def run(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point."""
    req_data = state.get("parsed_requirement")
    qual_data = state.get("qualification_result")
    report_data = state.get("intelligence_reports")

    if not req_data or not qual_data:
        return {"errors": [{"stage": "rfq", "error": "Missing required state data"}]}

    result = await generate_rfq_package(
        ParsedRequirement(**req_data),
        QualificationResult(**qual_data),
        IntelligenceReportResult(**(report_data or {})),
        buyer_company=state.get("buyer_company", ""),
        buyer_contact_name=state.get("buyer_contact_name", ""),
        buyer_contact_email=state.get("buyer_contact_email", ""),
    )

    return {
        "rfq_result": result.model_dump(),
        "current_stage": "rfq",
        "messages": [{"role": "system", "content": f"RFQ package generated for {len(result.outreach_records)} suppliers. Awaiting approval to send."}],
    }
