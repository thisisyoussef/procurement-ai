"""Response models for the supplier profile aggregation endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SupplierProfileHeroStats(BaseModel):
    unit_price: str | None = None
    unit_price_source: str = "estimate"  # "estimate" | "quoted"
    moq: str | None = None
    lead_time: str | None = None
    google_rating: float | None = None
    google_review_count: int | None = None
    response_time_hours: float | None = None


class SupplierProfileQuote(BaseModel):
    unit_price: str | None = None
    currency: str = "USD"
    moq: str | None = None
    lead_time: str | None = None
    payment_terms: str | None = None
    shipping_terms: str | None = None
    validity_period: str | None = None
    notes: str | None = None
    source: str = "estimate"  # "estimate" | "parsed_response"
    confidence_score: float = 0.0
    quantity: int | None = None


class SupplierProfileAssessment(BaseModel):
    reasoning: str = ""
    confidence: str = "low"
    best_for: str = ""
    rank: int | None = None
    overall_score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class SupplierProfileVerificationCheck(BaseModel):
    check_type: str
    status: str
    score: float = 0.0
    details: str = ""


class SupplierProfileVerification(BaseModel):
    composite_score: float = 0.0
    risk_level: str = "unknown"
    recommendation: str = "pending"
    summary: str = ""
    checks: list[SupplierProfileVerificationCheck] = Field(default_factory=list)


class SupplierProfileCompanyDetails(BaseModel):
    address: str | None = None
    city: str | None = None
    country: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    preferred_contact_method: str = "email"
    language: str | None = None
    categories: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    source: str = "unknown"
    is_intermediary: bool = False


class SupplierProfileCommMessage(BaseModel):
    message_key: str
    direction: str
    channel: str = "email"
    subject: str | None = None
    body_preview: str | None = None
    delivery_status: str = "unknown"
    created_at: float = 0.0
    source: str | None = None


class SupplierProfileOutreachStatus(BaseModel):
    email_sent: bool = False
    response_received: bool = False
    delivery_status: str = "unknown"
    follow_ups_sent: int = 0
    excluded: bool = False
    exclusion_reason: str | None = None


class SupplierProfileResponse(BaseModel):
    supplier_index: int
    name: str
    description: str | None = None
    hero_stats: SupplierProfileHeroStats
    quote: SupplierProfileQuote | None = None
    assessment: SupplierProfileAssessment | None = None
    verification: SupplierProfileVerification | None = None
    company: SupplierProfileCompanyDetails
    outreach: SupplierProfileOutreachStatus | None = None
    communication_log: list[SupplierProfileCommMessage] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] | None = None
