"""Supplier ORM models."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(1000))
    email: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    categories: Mapped[list | None] = mapped_column(ARRAY(String(200)))
    certifications: Mapped[list | None] = mapped_column(ARRAY(String(200)))
    year_established: Mapped[int | None] = mapped_column(Integer)
    employee_count: Mapped[str | None] = mapped_column(String(100))
    moq_range: Mapped[str | None] = mapped_column(String(200))
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    verification_score: Mapped[float] = mapped_column(Float, default=0.0)
    verification_data: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(
        String(100), nullable=False, default="manual"
    )  # thomasnet, alibaba, google, importyeti, manual
    google_rating: Mapped[float | None] = mapped_column(Float)
    google_review_count: Mapped[int | None] = mapped_column(Integer)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding = mapped_column(Vector(1536), nullable=True)  # text-embedding-3-small

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.name} ({self.source})>"
