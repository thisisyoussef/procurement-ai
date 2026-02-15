"""Downstream feedback signal processing for supplier and user learning loops."""

from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.database import async_session_factory
from app.repositories import supplier_repository as supplier_repo

logger = logging.getLogger(__name__)


class FeedbackSignal(BaseModel):
    """A correction or learning signal from a downstream agent."""

    source_agent: str
    target: str
    signal_type: str
    supplier_id: str | None = None
    supplier_name: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


async def emit_feedback(signal: FeedbackSignal) -> None:
    """Process a feedback signal and update relevant stores best-effort."""
    logger.info(
        "Feedback signal received: source=%s target=%s type=%s supplier=%s",
        signal.source_agent,
        signal.target,
        signal.signal_type,
        signal.supplier_id or signal.supplier_name,
    )

    # Supplier-level feedback persists as interactions for now.
    if signal.target == "supplier" and (signal.supplier_id or signal.supplier_name):
        try:
            async with async_session_factory() as session:
                if signal.supplier_id:
                    await supplier_repo.create_supplier_interaction(
                        session=session,
                        supplier_id=signal.supplier_id,
                        interaction_type=signal.signal_type,
                        source=f"feedback:{signal.source_agent}",
                        details=signal.data,
                    )
                    await session.commit()
        except Exception:  # noqa: BLE001
            logger.warning("Failed to persist supplier feedback signal", exc_info=True)

    # User profile and discovery-targeted learning are intentionally no-op
    # until richer persistence tables are introduced.
