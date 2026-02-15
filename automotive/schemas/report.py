"""Schemas for Agent 5 — Intelligence Report Generator output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RiskAssessment(BaseModel):
    """Individual risk entry in an intelligence report."""

    risk_type: str = ""
    description: str = ""
    severity: str = "low"
    mitigation: str = ""


class IntelligenceReport(BaseModel):
    """Comprehensive intelligence brief for a single supplier."""

    supplier_id: str
    company_name: str

    # Report sections
    executive_summary: str = ""
    company_profile: str = ""
    capability_assessment: str = ""
    quality_credentials: str = ""
    financial_health: str = ""
    geographic_analysis: str = ""
    competitive_positioning: str = ""

    # Structured risk assessment
    risks: list[RiskAssessment] = Field(default_factory=list)

    # Recommended next steps
    recommended_questions: list[str] = Field(default_factory=list)
    areas_to_probe: list[str] = Field(default_factory=list)
    rfq_focus_areas: list[str] = Field(default_factory=list)

    # Contact info
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    website: str = ""
    address: str = ""


class IntelligenceReportResult(BaseModel):
    """Complete output from the Intelligence Report Generator."""

    reports: list[IntelligenceReport] = Field(default_factory=list)
    overall_market_summary: str = ""
