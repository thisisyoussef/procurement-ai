"""Schemas for Agent 2 — Supplier Discovery output."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DiscoveredSupplier(BaseModel):
    """A supplier found during the discovery phase."""

    supplier_id: str = Field(description="Internal UUID")
    company_name: str
    headquarters: str = ""
    manufacturing_locations: list[str] = Field(default_factory=list)
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    # Discovery metadata
    sources: list[str] = Field(default_factory=list, description="Which databases found this supplier")
    initial_score: float = Field(default=0.0, ge=0, le=100, description="Composite discovery score 0–100")
    capability_match: float = Field(default=0.0, ge=0, le=100)
    certification_match: float = Field(default=0.0, ge=0, le=100)
    geographic_fit: float = Field(default=0.0, ge=0, le=100)
    scale_fit: float = Field(default=0.0, ge=0, le=100)
    data_richness: float = Field(default=0.0, ge=0, le=100)

    # Known information (may be partial)
    known_processes: list[str] = Field(default_factory=list)
    known_materials: list[str] = Field(default_factory=list)
    known_certifications: list[str] = Field(default_factory=list)
    employee_count: Optional[int] = None
    estimated_revenue: Optional[str] = None

    # Flags
    previously_known: bool = False
    trade_data_confirmed: bool = False


class DiscoveryResult(BaseModel):
    """Complete output from the Supplier Discovery agent."""

    total_found: int = 0
    sources_searched: list[str] = Field(default_factory=list)
    suppliers: list[DiscoveredSupplier] = Field(default_factory=list)
    search_queries_used: list[str] = Field(default_factory=list)
    gaps_identified: list[str] = Field(default_factory=list, description="Areas where coverage was thin")
