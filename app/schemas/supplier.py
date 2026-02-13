"""Supplier API request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SupplierResponse(BaseModel):
    id: UUID
    name: str
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    description: str | None = None
    categories: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    verification_score: float = 0.0
    source: str = "unknown"
    google_rating: float | None = None
    google_review_count: int | None = None
    is_verified: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
