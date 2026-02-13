"""Project timeline event persistence and in-project timeline helpers."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.models.dashboard import ProjectEvent
from app.repositories import dashboard_repository as dashboard_repo

logger = logging.getLogger(__name__)
settings = get_settings()

_project_events_schema_ready = False


async def _ensure_project_events_schema() -> None:
    global _project_events_schema_ready
    if _project_events_schema_ready:
        return

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: ProjectEvent.__table__.create(sync_conn, checkfirst=True))
    _project_events_schema_ready = True


def _normalize_uuid(value: str | uuid.UUID | None) -> str | None:
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except Exception:  # noqa: BLE001
        return None


async def record_project_event(
    project: dict[str, Any],
    *,
    event_type: str,
    title: str,
    description: str | None = None,
    priority: str = "info",
    phase: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a project event in both runtime project state and DB table."""
    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "title": title,
        "description": description or "",
        "priority": priority,
        "phase": phase,
        "payload": payload or {},
        "timestamp": time.time(),
    }

    timeline = project.setdefault("timeline_events", [])
    timeline.append(event)
    if len(timeline) > 500:
        project["timeline_events"] = timeline[-500:]

    if (settings.project_store_backend or "database").lower() != "database":
        return event

    user_id = _normalize_uuid(project.get("user_id"))
    project_id = _normalize_uuid(project.get("id"))
    if not user_id or not project_id:
        return event

    try:
        await _ensure_project_events_schema()
        async with async_session_factory() as session:
            await dashboard_repo.create_project_event(
                session=session,
                user_id=user_id,
                project_id=project_id,
                event_type=event_type,
                title=title,
                description=description,
                priority=priority,
                phase=phase,
                payload=payload,
            )
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("Failed to persist project event %s for project %s", event_type, project_id, exc_info=True)

    return event
