"""Buyer context schemas used to personalize sourcing across the pipeline."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LogisticsProfile(BaseModel):
    """Shipping and import logistics for the buyer."""

    shipping_address: str | None = None
    shipping_city: str | None = None
    shipping_state: str | None = None
    shipping_country: str | None = None
    shipping_zip: str | None = None
    port_of_entry: str | None = None
    has_freight_forwarder: bool | None = None
    has_customs_broker: bool | None = None
    fulfillment_type: str | None = None
    fulfillment_provider: str | None = None
    import_experience: str | None = None
    preferred_incoterms: str | None = None


class FinancialProfile(BaseModel):
    """Budget and payment capabilities."""

    budget_hard_cap: float | None = None
    budget_currency: str = "USD"
    payment_methods: list[str] = Field(default_factory=list)
    can_pay_deposit: bool | None = None
    max_deposit_amount: float | None = None
    payment_terms_preference: str | None = None


class TimelineContext(BaseModel):
    """Deadline and urgency context."""

    hard_deadline: date | None = None
    deadline_reason: str | None = None
    buffer_weeks: int | None = None
    urgency_level: str | None = None


class QualityContext(BaseModel):
    """Quality standards and requirements."""

    use_case: str | None = None
    quality_tier: str | None = None
    needs_samples_first: bool | None = None
    inspection_requirements: str | None = None
    defect_tolerance: str | None = None
    industry_standards: list[str] = Field(default_factory=list)


class CommunicationPreferences(BaseModel):
    """How the buyer prefers to interact with suppliers."""

    preferred_language: str = "en"
    needs_english_speaking_contact: bool | None = None
    preferred_channel: str | None = None
    timezone: str | None = None
    response_expectation: str | None = None


class BuyerContext(BaseModel):
    """Complete buyer context threaded through every agent."""

    logistics: LogisticsProfile = Field(default_factory=LogisticsProfile)
    financial: FinancialProfile = Field(default_factory=FinancialProfile)
    timeline: TimelineContext = Field(default_factory=TimelineContext)
    quality: QualityContext = Field(default_factory=QualityContext)
    communication: CommunicationPreferences = Field(default_factory=CommunicationPreferences)

    is_first_import: bool | None = None
    sourced_this_category_before: bool | None = None
    previous_supplier_names: list[str] = Field(default_factory=list)
    category_experience_level: str | None = None
    priority_tradeoff: str | None = None

    explicitly_provided_fields: list[str] = Field(default_factory=list)
    inferred_fields: list[str] = Field(default_factory=list)
