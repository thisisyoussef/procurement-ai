"""Schemas for Agent 3 — Supplier Qualification & Verification output."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _coerce_str_list(v: object) -> list[str]:
    """Coerce LLM output that should be a list[str] but sometimes arrives as a plain string."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        parts = re.split(r"[,;\n]+", v)
        return [p.strip() for p in parts if p.strip()]
    return []


class WebsiteCapabilities(BaseModel):
    """Structured capabilities extracted from a supplier's website via Firecrawl."""

    company_description: str = ""
    manufacturing_processes: list[str] = Field(default_factory=list)
    materials_processed: list[str] = Field(default_factory=list)
    equipment_list: list[str] = Field(default_factory=list, description="e.g. 600-ton stamping press")
    certifications_claimed: list[str] = Field(default_factory=list)
    industries_served: list[str] = Field(default_factory=list)
    key_customers: list[str] = Field(default_factory=list)
    capacity_indicators: list[str] = Field(default_factory=list, description="e.g. 200,000 sq ft facility")
    secondary_operations: list[str] = Field(default_factory=list)
    prototype_capability: bool = False
    geographic_notes: str = ""

    @field_validator(
        "manufacturing_processes", "materials_processed", "equipment_list",
        "certifications_claimed", "industries_served", "key_customers",
        "capacity_indicators", "secondary_operations",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, v: object) -> list[str]:
        return _coerce_str_list(v)


class QualifiedSupplier(BaseModel):
    """A supplier that has been through the full verification pipeline."""

    supplier_id: str
    company_name: str
    qualification_status: Literal["qualified", "conditional", "disqualified"]

    # IATF 16949 verification
    iatf_status: str = "unknown"
    iatf_cert_number: Optional[str] = None
    iatf_scope: Optional[str] = None
    iatf_expiry: Optional[str] = None

    # Financial health (D&B)
    financial_risk: str = "unknown"
    duns_number: Optional[str] = None
    paydex_score: Optional[int] = None
    estimated_revenue: Optional[str] = None
    employee_count: Optional[int] = None
    years_in_business: Optional[int] = None

    # Corporate registration
    corporate_status: str = "unknown"

    # Website intelligence
    capabilities: WebsiteCapabilities = Field(default_factory=WebsiteCapabilities)

    # Reputation
    reputation_score: float = Field(default=0.0, ge=0, le=100)
    google_rating: Optional[float] = None
    review_count: Optional[int] = None

    # Qualification rationale
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    disqualification_reason: Optional[str] = None
    overall_confidence: float = Field(default=0.0, ge=0, le=1)

    # Carry forward from discovery
    website: Optional[str] = None
    headquarters: str = ""
    manufacturing_locations: list[str] = Field(default_factory=list)
    phone: Optional[str] = None
    email: Optional[str] = None
    sources: list[str] = Field(default_factory=list)


class QualificationResult(BaseModel):
    """Complete output from the Qualification agent."""

    qualified_count: int = 0
    conditional_count: int = 0
    disqualified_count: int = 0
    suppliers: list[QualifiedSupplier] = Field(default_factory=list)
    verification_summary: str = ""
