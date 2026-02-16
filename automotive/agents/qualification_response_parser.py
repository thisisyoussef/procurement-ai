"""Qualification Response Parser — extracts structured data from supplier email replies.

Uses LLM structured output to parse free-text supplier responses into the
QualificationResponseParsed schema, then optionally re-renders the qualification verdict.
"""

import logging
from datetime import datetime, timezone

from automotive.core.config import MODEL_TIER_BALANCED
from automotive.core.llm import call_llm_structured
from automotive.schemas.qualification import (
    QualificationResponseParsed,
    QualificationResult,
    QualifiedSupplier,
)
from automotive.schemas.requirements import ParsedRequirement

logger = logging.getLogger(__name__)

RESPONSE_PARSER_SYSTEM = """\
You are parsing a supplier's email response to a qualification questionnaire.

Extract structured data from the response text. The supplier may answer some or
all of the questions. Extract what you can with confidence.

Rules:
- If the supplier confirms IATF 16949, set iatf_confirmed=true and extract cert details.
- If they deny it or say "in progress", set iatf_confirmed=false and note it.
- For capacity, lead times, and experience — extract the supplier's own words concisely.
- List any certifications they mention (ISO 9001, IATF 16949, ISO 14001, NADCAP, etc.)
- Set confidence 0.0-1.0 based on how complete and clear the response is.
  - 0.8-1.0: Detailed, clear answers to most questions
  - 0.5-0.7: Partial answers, some ambiguity
  - 0.2-0.4: Vague or minimal response
  - 0.0-0.1: Response doesn't address the questions
"""


async def parse_qualification_response(
    supplier_name: str,
    response_text: str,
    questions_asked: list[str] | None = None,
    requirement: ParsedRequirement | None = None,
) -> QualificationResponseParsed:
    """Parse a supplier's qualification response email into structured data."""
    schema = {
        "type": "object",
        "properties": {
            "iatf_confirmed": {"type": ["boolean", "null"]},
            "iatf_cert_number": {"type": ["string", "null"]},
            "iatf_expiry": {"type": ["string", "null"]},
            "capacity_description": {"type": ["string", "null"]},
            "lead_time_estimate": {"type": ["string", "null"]},
            "similar_projects": {"type": ["string", "null"]},
            "additional_certifications": {"type": "array", "items": {"type": "string"}},
            "financial_info": {"type": ["string", "null"]},
            "notes": {"type": ["string", "null"]},
            "confidence": {"type": "number"},
        },
        "required": ["confidence"],
    }

    context_lines = [f"Supplier: {supplier_name}"]
    if questions_asked:
        context_lines.append("Questions we asked:")
        for i, q in enumerate(questions_asked, 1):
            context_lines.append(f"  {i}. {q}")
    if requirement:
        context_lines.append(f"Part context: {requirement.part_description} ({requirement.manufacturing_process})")

    user_msg = (
        f"{chr(10).join(context_lines)}\n\n"
        f"=== SUPPLIER RESPONSE ===\n"
        f"{response_text}\n"
        f"=== END RESPONSE ===\n\n"
        f"Extract structured qualification data from the response above."
    )

    try:
        result = await call_llm_structured(
            system=RESPONSE_PARSER_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_BALANCED,
            max_tokens=1024,
        )
        return QualificationResponseParsed(**result)
    except Exception:
        logger.exception("Failed to parse qualification response from %s", supplier_name)
        return QualificationResponseParsed(
            notes="Failed to parse response automatically — manual review recommended",
            confidence=0.1,
        )


def apply_response_to_supplier(
    supplier: QualifiedSupplier,
    parsed: QualificationResponseParsed,
) -> QualifiedSupplier:
    """Apply parsed response data back to the supplier record."""
    now_iso = datetime.now(timezone.utc).isoformat()

    supplier.qualification_email_status = "responded"
    supplier.qualification_email_responded_at = now_iso
    supplier.qual_response = parsed.model_dump()

    # Update IATF if confirmed
    if parsed.iatf_confirmed is True:
        supplier.iatf_status = "evidence_found"
        if parsed.iatf_cert_number:
            supplier.iatf_cert_number = parsed.iatf_cert_number
        if parsed.iatf_expiry:
            supplier.iatf_expiry = parsed.iatf_expiry
        # Add to strengths if not already there
        iatf_strength = "IATF 16949 confirmed via email response"
        if iatf_strength not in supplier.strengths:
            supplier.strengths.append(iatf_strength)
    elif parsed.iatf_confirmed is False:
        supplier.iatf_status = "not_found"
        concern = "Supplier confirmed they do not hold IATF 16949 certification"
        if concern not in supplier.concerns:
            supplier.concerns.append(concern)

    # Update certifications
    if parsed.additional_certifications:
        for cert in parsed.additional_certifications:
            if cert not in supplier.capabilities.certifications_claimed:
                supplier.capabilities.certifications_claimed.append(cert)

    # Timeline entry
    summary_parts = []
    if parsed.iatf_confirmed is True:
        summary_parts.append("IATF confirmed")
    elif parsed.iatf_confirmed is False:
        summary_parts.append("No IATF")
    if parsed.capacity_description:
        summary_parts.append(f"capacity: {parsed.capacity_description[:60]}")
    if parsed.lead_time_estimate:
        summary_parts.append(f"lead time: {parsed.lead_time_estimate}")
    if parsed.similar_projects:
        summary_parts.append("relevant experience noted")
    if parsed.additional_certifications:
        summary_parts.append(f"certs: {', '.join(parsed.additional_certifications[:3])}")

    supplier.qualification_events.append({
        "timestamp": now_iso,
        "event": "response_parsed",
        "detail": f"Response parsed (confidence {parsed.confidence:.0%}): {' · '.join(summary_parts) or 'minimal info extracted'}",
    })

    # Potentially upgrade qualification status
    if supplier.qualification_status == "conditional" and parsed.confidence >= 0.6:
        # Check if key concerns are now addressed
        if parsed.iatf_confirmed is True and parsed.capacity_description:
            supplier.qualification_status = "qualified"
            supplier.qualification_events.append({
                "timestamp": now_iso,
                "event": "status_upgraded",
                "detail": "Upgraded from conditional → qualified based on email response",
            })
            supplier.overall_confidence = min(1.0, supplier.overall_confidence + 0.2)

    return supplier


async def parse_and_apply_response(
    qualification_result: QualificationResult,
    supplier_id: str,
    response_text: str,
    requirement: ParsedRequirement | None = None,
) -> QualificationResult:
    """Parse a supplier response and apply it to the qualification result."""
    supplier = next((s for s in qualification_result.suppliers if s.supplier_id == supplier_id), None)
    if not supplier:
        logger.warning("Supplier %s not found in qualification result", supplier_id)
        return qualification_result

    parsed = await parse_qualification_response(
        supplier_name=supplier.company_name,
        response_text=response_text,
        requirement=requirement,
    )

    apply_response_to_supplier(supplier, parsed)

    # Update outreach counts
    qualification_result.outreach_responded_count = sum(
        1 for s in qualification_result.suppliers if s.qualification_email_status == "responded"
    )
    qualification_result.outreach_pending_count = sum(
        1 for s in qualification_result.suppliers if s.qualification_email_status in ("sent", "delivered", "opened")
    )

    return qualification_result
