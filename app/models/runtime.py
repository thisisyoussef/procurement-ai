"""Runtime persistence models for project state, leads, and analytics events."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RuntimeProject(Base):
    __tablename__ = "runtime_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    product_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="parsing")
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="parsing")
    error: Mapped[str | None] = mapped_column(Text)
    state: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LandingLead(Base):
    __tablename__ = "landing_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    sourcing_note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100), default="landing_early_access")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(120))
    path: Mapped[str | None] = mapped_column(String(500))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
