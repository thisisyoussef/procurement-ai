"""Qualification Email Outreach — sends targeted questionnaire emails to suppliers.

Analyses data gaps from auto-checks and generates personalized questionnaire emails
asking suppliers to confirm the specific items that online checks couldn't verify.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.email_service import build_rfq_html, send_email
from automotive.api.v1.events import emit_activity
from automotive.core.config import MODEL_TIER_BALANCED
from automotive.core.llm import call_llm_structured
from automotive.schemas.qualification import QualificationResult, QualifiedSupplier
from automotive.schemas.requirements import ParsedRequirement

logger = logging.getLogger(__name__)

QUALIFICATION_EMAIL_SYSTEM = """\
You are writing a short, professional email on behalf of a buyer's sourcing team.

The purpose is a **capability questionnaire** — you are asking the supplier to confirm
specific items about their company so the buyer can complete their evaluation.

Guidelines:
- Keep under 250 words. Be direct and professional.
- Open with a brief context: who the buyer is and what they're sourcing.
- List the specific questions clearly (numbered list).
- Only ask about the data gaps provided — don't add extra questions.
- Close with a simple "please reply to this email" instruction and a timeline ask.
- Do NOT include attachments or legal terms — this is an initial screening, not an RFQ.
- Subject line: under 60 chars, mention "Supplier Qualification" and the buyer name.
"""


def _identify_data_gaps(supplier: QualifiedSupplier) -> list[str]:
    """Determine what questions to ask based on missing/unavailable data."""
    gaps: list[str] = []

    # IATF certification
    if supplier.iatf_status in ("data_unavailable", "unknown", "not_found", "check_failed"):
        gaps.append(
            "Do you hold an active IATF 16949 certification? If so, please provide "
            "the certificate number, certifying body, scope, and expiry date."
        )

    # Financial health
    if supplier.financial_risk in ("data_unavailable", "unknown", "check_failed"):
        gaps.append(
            "Can you share approximate annual revenue, years in business, and "
            "number of employees? (Ranges are fine — e.g. $10-50M, 100-250 staff.)"
        )

    # Manufacturing capability gaps
    if not supplier.capabilities.manufacturing_processes:
        gaps.append(
            "What manufacturing processes do you operate in-house? "
            "(e.g. stamping, CNC machining, injection molding, welding, assembly)"
        )

    if not supplier.capabilities.equipment_list:
        gaps.append(
            "What are your key pieces of equipment and their capacities? "
            "(e.g. 600-ton stamping press, 5-axis CNC)"
        )

    # Capacity
    if not supplier.capabilities.capacity_indicators:
        gaps.append(
            "What is your current production capacity and facility size? "
            "Are you able to accommodate new programs?"
        )

    # Additional certifications
    if not supplier.capabilities.certifications_claimed:
        gaps.append(
            "What quality and industry certifications do you currently hold? "
            "(e.g. ISO 9001, IATF 16949, ISO 14001, NADCAP)"
        )

    # Always ask about relevant experience
    gaps.append(
        "Do you have experience with similar parts or projects? "
        "Can you share examples of comparable work (without disclosing confidential customer details)?"
    )

    return gaps


async def _generate_qualification_email(
    supplier: QualifiedSupplier,
    requirement: ParsedRequirement,
    data_gaps: list[str],
    buyer_company: str,
    buyer_contact_name: str,
) -> dict[str, str]:
    """Use LLM to generate a personalized qualification questionnaire email."""
    schema = {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["subject", "body"],
    }

    numbered_questions = "\n".join(f"{i+1}. {q}" for i, q in enumerate(data_gaps))

    user_msg = (
        f"Generate a qualification questionnaire email.\n\n"
        f"Buyer: {buyer_company} (contact: {buyer_contact_name})\n"
        f"Supplier: {supplier.company_name}\n"
        f"Supplier location: {supplier.headquarters}\n\n"
        f"Opportunity context: Sourcing {requirement.part_description} "
        f"({requirement.manufacturing_process}, {requirement.material_family}), "
        f"volume ~{requirement.annual_volume}/year.\n\n"
        f"Questions to ask (include ALL of these in the email):\n{numbered_questions}"
    )

    try:
        result = await call_llm_structured(
            system=QUALIFICATION_EMAIL_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_BALANCED,
            max_tokens=1024,
        )
        return result
    except Exception:
        logger.exception("Email generation failed for %s", supplier.company_name)
        return {
            "subject": f"Supplier Qualification – {buyer_company}",
            "body": (
                f"Dear {supplier.company_name},\n\n"
                f"We are evaluating suppliers for an upcoming project and would like "
                f"to learn more about your capabilities.\n\n"
                f"Could you please provide information on the following:\n"
                f"{numbered_questions}\n\n"
                f"Please reply to this email at your earliest convenience.\n\n"
                f"Best regards,\n{buyer_contact_name}\n{buyer_company}"
            ),
        }


async def send_qualification_emails(
    project_id: str,
    supplier_ids: list[str],
    qualification_result: QualificationResult,
    requirement: ParsedRequirement,
    buyer_company: str = "",
    buyer_contact_name: str = "",
    buyer_contact_email: str = "",
) -> QualificationResult:
    """Send qualification questionnaire emails to selected suppliers.

    For each supplier:
    1. Identify data gaps from auto-check results
    2. Generate personalized questionnaire via LLM
    3. Send via Resend with tracking headers
    4. Update supplier fields and timeline
    """
    supplier_map = {s.supplier_id: s for s in qualification_result.suppliers}
    sent_count = 0

    for sid in supplier_ids:
        supplier = supplier_map.get(sid)
        if not supplier:
            logger.warning("Supplier %s not found in qualification result", sid)
            continue

        if not supplier.email:
            # No email address — skip with timeline entry
            now_iso = datetime.now(timezone.utc).isoformat()
            supplier.qualification_email_status = "skipped"
            supplier.qualification_events.append({
                "timestamp": now_iso,
                "event": "email_skipped",
                "detail": "No email address available for this supplier",
            })
            emit_activity("qualify", "warning", f"No email for {supplier.company_name} — skipped", project_id=project_id)
            continue

        if supplier.qualification_email_status not in ("not_sent", "bounced"):
            # Already sent or already responded — skip
            logger.info("Skipping %s — email status is %s", supplier.company_name, supplier.qualification_email_status)
            continue

        # Identify data gaps
        data_gaps = _identify_data_gaps(supplier)
        if not data_gaps:
            supplier.qualification_email_status = "skipped"
            supplier.qualification_events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "email_skipped",
                "detail": "All verification data already available — no questions to ask",
            })
            continue

        # Generate email
        email_content = await _generate_qualification_email(
            supplier, requirement, data_gaps, buyer_company, buyer_contact_name,
        )

        # Send via Resend
        body_html = build_rfq_html(email_content["body"])
        result = await send_email(
            to=supplier.email,
            subject=email_content["subject"],
            body_html=body_html,
            reply_to=buyer_contact_email or None,
            headers={
                "X-Procurement-Project-Id": project_id,
                "X-Procurement-Supplier-Id": supplier.supplier_id,
                "X-Procurement-Email-Type": "qualification",
            },
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        if result.get("sent"):
            supplier.qualification_email_status = "sent"
            supplier.qualification_email_id = result.get("id", "")
            supplier.qualification_email_sent_at = now_iso
            supplier.qualification_events.append({
                "timestamp": now_iso,
                "event": "email_sent",
                "detail": f"Qualification questionnaire sent to {supplier.email} ({len(data_gaps)} questions)",
            })
            sent_count += 1
            emit_activity("qualify", "start", f"Questionnaire sent to {supplier.company_name}", project_id=project_id)
        else:
            error_msg = result.get("error", "Unknown send error")
            supplier.qualification_email_status = "bounced"
            supplier.qualification_events.append({
                "timestamp": now_iso,
                "event": "email_failed",
                "detail": f"Failed to send: {error_msg}",
            })
            emit_activity("qualify", "error", f"Email to {supplier.company_name} failed: {error_msg}", project_id=project_id)

    # Update outreach counts
    qualification_result.outreach_sent_count = sum(
        1 for s in qualification_result.suppliers if s.qualification_email_status in ("sent", "delivered", "opened", "responded")
    )
    qualification_result.outreach_responded_count = sum(
        1 for s in qualification_result.suppliers if s.qualification_email_status == "responded"
    )
    qualification_result.outreach_pending_count = sum(
        1 for s in qualification_result.suppliers if s.qualification_email_status in ("sent", "delivered", "opened")
    )

    emit_activity("qualify", "complete", f"Sent {sent_count} qualification questionnaires", project_id=project_id)
    return qualification_result
