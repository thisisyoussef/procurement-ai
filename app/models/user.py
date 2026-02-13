"""User model — maps to Supabase Auth users."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(500))
    avatar_url: Mapped[str | None] = mapped_column(String(2000))
    company_name: Mapped[str | None] = mapped_column(String(500))
    plan: Mapped[str] = mapped_column(String(50), default="free_trial")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
