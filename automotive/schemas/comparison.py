"""Schemas for Agent 4 — Comparison & Ranking Engine output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SupplierComparison(BaseModel):
    """Scored comparison entry for one supplier."""

    supplier_id: str
    company_name: str

    # Scores by dimension (0–100)
    capability_score: float = 0.0
    quality_score: float = 0.0
    geographic_score: float = 0.0
    financial_score: float = 0.0
    scale_score: float = 0.0
    reputation_score: float = 0.0
    composite_score: float = 0.0

    # Narratives
    capability_narrative: str = ""
    quality_narrative: str = ""
    geographic_narrative: str = ""
    financial_narrative: str = ""

    # Differentiation
    unique_strengths: list[str] = Field(default_factory=list)
    notable_risks: list[str] = Field(default_factory=list)
    best_fit_for: str = ""


class ComparisonMatrix(BaseModel):
    """Complete comparison output for all qualified suppliers."""

    requirement_summary: str = ""
    comparison_date: str = ""
    weight_profile: dict[str, float] = Field(
        default_factory=lambda: {
            "capability": 0.25,
            "quality": 0.25,
            "geography": 0.20,
            "financial": 0.15,
            "scale": 0.10,
            "reputation": 0.05,
        }
    )

    suppliers: list[SupplierComparison] = Field(default_factory=list)
    overall_ranking: list[str] = Field(default_factory=list, description="Supplier IDs in ranked order")
    top_recommendation: str = ""
    recommendation_rationale: str = ""
