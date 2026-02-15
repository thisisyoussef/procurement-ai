"""Schemas for proactive intelligence alerts."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field


class ProactiveAlert(BaseModel):
    id: str
    title: str
    message: str
    severity: str = "info"
    created_at: float = Field(default_factory=time.time)
    expires_at: float | None = None
    source: str = "proactive_intelligence"
    metadata: dict[str, str] = Field(default_factory=dict)
