"""SQLAlchemy models for automotive procurement projects."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AutomotiveProject(Base):
    __tablename__ = "automotive_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    org_id: Mapped[str] = mapped_column(String(255), default="default")

    # Request
    raw_request: Mapped[str] = mapped_column(Text, default="")
    parsed_requirement: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Pipeline state
    current_stage: Mapped[str] = mapped_column(String(50), default="parse")
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Stage results (JSON blobs)
    discovery_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    qualification_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comparison_matrix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    intelligence_reports: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rfq_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quote_ingestion: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Approvals tracking
    approvals: Mapped[dict] = mapped_column(JSON, default=dict)
    human_overrides: Mapped[dict] = mapped_column(JSON, default=dict)
    weight_profile: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "capability": 0.25,
            "quality": 0.25,
            "geography": 0.20,
            "financial": 0.15,
            "scale": 0.10,
            "reputation": 0.05,
        },
    )

    # Buyer info
    buyer_company: Mapped[str] = mapped_column(String(255), default="")
    buyer_contact_name: Mapped[str] = mapped_column(String(255), default="")
    buyer_contact_email: Mapped[str] = mapped_column(String(255), default="")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    events: Mapped[list[AutomotiveProjectEvent]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    suppliers: Mapped[list[AutomotiveSupplier]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )


class AutomotiveProjectEvent(Base):
    __tablename__ = "automotive_project_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automotive_projects.id", ondelete="CASCADE")
    )
    stage: Mapped[str] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped[AutomotiveProject] = relationship(back_populates="events")


class AutomotiveSupplier(Base):
    __tablename__ = "automotive_suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automotive_projects.id", ondelete="CASCADE")
    )

    company_name: Mapped[str] = mapped_column(String(500))
    headquarters: Mapped[str] = mapped_column(String(500), default="")
    website: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Qualification
    qualification_status: Mapped[str] = mapped_column(String(50), default="pending")
    iatf_status: Mapped[str] = mapped_column(String(50), default="unknown")
    financial_risk: Mapped[str] = mapped_column(String(50), default="unknown")

    # Full profile (JSON blob)
    profile_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Scores
    composite_score: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped[AutomotiveProject] = relationship(back_populates="suppliers")
