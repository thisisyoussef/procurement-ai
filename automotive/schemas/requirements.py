"""Schemas for Agent 1 — Requirements Parser output."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _coerce_optional_int(v: object) -> int | None:
    """Coerce LLM output to int or None.

    The LLM sometimes returns descriptive strings like
    'Samples for durability testing (quantity not specified)'
    instead of an integer. We try to extract a number; if we can't, return None.
    """
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        v = v.strip().replace(",", "")
        # Try direct parse first
        try:
            return int(v)
        except ValueError:
            pass
        # Try to extract first number from the string
        match = re.search(r"\d+", v)
        if match:
            return int(match.group())
        return None
    return None


class ParsedRequirement(BaseModel):
    """Structured procurement specification extracted from natural language."""

    # Part identification
    part_description: str = Field(description="Concise description of the part needed")
    part_category: Literal[
        "stamping", "die_casting", "injection_molding", "cnc_machining",
        "forging", "pcba", "wiring_harness", "rubber_sealing", "assembly", "other",
    ] = Field(description="Primary manufacturing category")

    # Material
    material_family: str = Field(description="Material family: steel, aluminum, plastic, etc.")
    material_spec: Optional[str] = Field(default=None, description="Specific grade: SPCC, A380, PA66-GF30")

    # Process
    manufacturing_process: str = Field(description="Primary manufacturing process")
    secondary_operations: list[str] = Field(default_factory=list, description="e.g. e-coat, heat treat, machining")

    # Volume
    annual_volume: int = Field(description="Annual production volume")
    lot_size: Optional[int] = Field(default=None, description="Per-shipment lot size")
    volume_confidence: Literal["exact", "estimated", "unknown"] = "estimated"

    # Quality
    tolerances: Optional[str] = Field(default=None, description="Tolerance requirements")
    surface_finish: Optional[str] = Field(default=None, description="Surface finish spec")
    certifications_required: list[str] = Field(default_factory=list, description="e.g. IATF 16949, ISO 14001")
    ppap_level: Optional[Literal["1", "2", "3", "4", "5"]] = Field(default=None)

    # Geography
    preferred_regions: list[str] = Field(default_factory=list, description="Mexico, US Midwest, etc.")
    geographic_constraints: Optional[str] = Field(default=None, description="e.g. USMCA compliant")
    max_distance_miles: Optional[int] = Field(default=None)
    buyer_plant_location: Optional[str] = Field(default=None)

    # Timeline
    prototype_needed: bool = False
    prototype_quantity: Optional[int] = Field(default=None)
    target_sop_date: Optional[str] = Field(default=None)
    urgency: Literal["standard", "expedited", "urgent"] = "standard"

    # Supplier preferences
    preferred_tier: Optional[Literal["tier1", "tier2", "tier3", "tier4"]] = Field(default=None)
    min_revenue: Optional[int] = Field(default=None, description="Minimum annual revenue USD")
    min_employees: Optional[int] = Field(default=None)

    # Meta
    ambiguities: list[str] = Field(default_factory=list, description="Fields needing human clarification")
    complexity_score: Literal["simple", "moderate", "complex"] = "moderate"
    estimated_tooling_range: str = Field(default="", description="e.g. $50K–$150K")
    estimated_lead_time: str = Field(default="", description="e.g. 12–16 weeks tooling")

    # ── Validators to coerce sloppy LLM output ──

    @field_validator("annual_volume", mode="before")
    @classmethod
    def _coerce_annual_volume(cls, v: object) -> int:
        result = _coerce_optional_int(v)
        return result if result is not None else 0

    @field_validator(
        "prototype_quantity", "lot_size", "max_distance_miles",
        "min_revenue", "min_employees",
        mode="before",
    )
    @classmethod
    def _coerce_opt_ints(cls, v: object) -> int | None:
        return _coerce_optional_int(v)


# JSON Schema for structured output extraction
PARSED_REQUIREMENT_SCHEMA = ParsedRequirement.model_json_schema()
