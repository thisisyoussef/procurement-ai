"""Persistent cross-project user sourcing profile schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SupplierRelationship(BaseModel):
    """A known supplier relationship from past projects."""

    supplier_id: str
    supplier_name: str
    sentiment: str
    notes: str | None = None
    last_interaction_date: date | None = None
    projects_together: int = 0
    quoted_prices: list[str] = Field(default_factory=list)
    communication_rating: str | None = None


class CategoryExperience(BaseModel):
    """Buyer's experience in a product category."""

    category: str
    projects_completed: int = 0
    preferred_regions: list[str] = Field(default_factory=list)
    typical_budget_range: str | None = None
    typical_quantity_range: str | None = None
    known_good_suppliers: list[str] = Field(default_factory=list)
    known_bad_suppliers: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)


class UserSourcingProfile(BaseModel):
    """Persistent profile that accumulates across all projects."""

    default_shipping_address: str | None = None
    default_port_of_entry: str | None = None
    default_payment_methods: list[str] = Field(default_factory=list)
    default_incoterms: str | None = None
    default_quality_tier: str | None = None
    import_experience_level: str = "unknown"

    preferred_sourcing_regions: list[str] = Field(default_factory=list)
    avoided_regions: list[str] = Field(default_factory=list)
    preferred_communication_language: str = "en"
    needs_english_contacts: bool = True
    price_sensitivity: str = "moderate"
    risk_tolerance: str = "moderate"

    supplier_relationships: list[SupplierRelationship] = Field(default_factory=list)
    category_experience: list[CategoryExperience] = Field(default_factory=list)

    total_projects: int = 0
    total_suppliers_contacted: int = 0
    average_project_budget: float | None = None
    most_common_categories: list[str] = Field(default_factory=list)
    last_project_date: date | None = None
