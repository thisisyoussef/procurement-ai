"""Post-project retrospective request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class RetrospectiveRequest(BaseModel):
    supplier_chosen: str | None = None
    overall_satisfaction: int | None = None
    communication_rating: int | None = None
    pricing_accuracy: str | None = None
    quality_notes: str | None = None
    would_use_again: bool | None = None
    what_went_wrong: str | None = None
    what_went_well: str | None = None


class RetrospectiveResponse(BaseModel):
    project_id: str
    status: str = "recorded"
