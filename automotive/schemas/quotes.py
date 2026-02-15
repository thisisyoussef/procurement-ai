"""Schemas for Agent 7 — Response Ingestion & Quote Structuring."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ParsedQuote(BaseModel):
    """Structured quote data extracted from a supplier's response."""

    supplier_id: str
    supplier_name: str
    received_date: str = ""

    # Pricing
    piece_price: float = 0.0
    piece_price_currency: str = "USD"
    price_breaks: list[dict] = Field(default_factory=list, description="[{volume: int, price: float}]")

    # Cost breakdown (if provided by supplier)
    material_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    overhead_cost: Optional[float] = None
    sga_cost: Optional[float] = None
    profit_margin: Optional[float] = None

    # Tooling
    tooling_cost: Optional[float] = None
    tooling_lead_time_weeks: Optional[int] = None
    tool_life_shots: Optional[int] = None
    tooling_ownership: Optional[str] = None

    # Logistics
    production_lead_time_weeks: Optional[int] = None
    moq: Optional[int] = None
    shipping_terms: Optional[str] = None

    # Normalized TCO
    normalized_piece_price_usd: float = 0.0
    estimated_annual_tco_usd: float = 0.0

    # Confidence
    extraction_confidence: float = Field(default=0.0, ge=0, le=1)
    low_confidence_fields: list[str] = Field(default_factory=list)
    raw_document_url: str = ""
    notes: list[str] = Field(default_factory=list)


class QuoteIngestionResult(BaseModel):
    """Complete output from the Response Ingestion agent."""

    quotes: list[ParsedQuote] = Field(default_factory=list)
    total_received: int = 0
    total_parsed: int = 0
    awaiting_response: list[str] = Field(default_factory=list, description="Supplier IDs still pending")
