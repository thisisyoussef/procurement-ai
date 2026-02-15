"""Schemas for Agent 6 — RFQ Preparation & Outreach."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RFQLineItem(BaseModel):
    part_number: str = ""
    description: str = ""
    revision: str = ""
    drawing_reference: str = ""
    material_spec: str = ""
    process_type: str = ""
    annual_volume: int = 0
    lot_size: int = 0
    price_break_volumes: list[int] = Field(default_factory=list)


class QualityRequirements(BaseModel):
    iatf_16949_required: bool = True
    ppap_level: Literal["1", "2", "3", "4", "5"] = "3"
    special_characteristics: list[str] = Field(default_factory=list)
    inspection_requirements: list[str] = Field(default_factory=list)
    gauge_requirements: Optional[str] = None


class DeliverySchedule(BaseModel):
    delivery_frequency: str = ""
    shipping_terms: str = "FOB Origin"
    lead_time_weeks: Optional[int] = None


class PackagingRequirements(BaseModel):
    packaging_type: str = ""
    returnable_containers: bool = False
    labeling_requirements: list[str] = Field(default_factory=list)


class ToolingTerms(BaseModel):
    tooling_ownership: str = "buyer"
    tooling_payment_terms: str = ""
    tool_maintenance_responsibility: str = "supplier"


class RFQPackage(BaseModel):
    """Complete RFQ document ready for review and sending."""

    rfq_id: str = ""
    rfq_date: str = ""
    response_deadline: str = ""
    buyer_company: str = ""
    buyer_contact_name: str = ""
    buyer_contact_email: str = ""
    program_name: Optional[str] = None

    line_items: list[RFQLineItem] = Field(default_factory=list)
    quality_block: QualityRequirements = Field(default_factory=QualityRequirements)
    delivery_schedule: DeliverySchedule = Field(default_factory=DeliverySchedule)
    packaging_requirements: PackagingRequirements = Field(default_factory=PackagingRequirements)
    tooling_terms: ToolingTerms = Field(default_factory=ToolingTerms)

    terms_reference: str = ""
    nda_required: bool = False

    # Generated email content
    email_subject: str = ""
    email_body: str = ""


class OutreachRecord(BaseModel):
    """Tracking record for one RFQ sent to one supplier."""

    supplier_id: str
    supplier_name: str
    recipient_email: str
    sent_at: Optional[str] = None
    delivery_status: str = "pending"
    opened: bool = False
    opened_at: Optional[str] = None
    responded: bool = False
    responded_at: Optional[str] = None
    bounced: bool = False


class RFQResult(BaseModel):
    """Complete output from the RFQ Outreach agent."""

    rfq_package: RFQPackage = Field(default_factory=RFQPackage)
    outreach_records: list[OutreachRecord] = Field(default_factory=list)
    total_sent: int = 0
    total_bounced: int = 0
