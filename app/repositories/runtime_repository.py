"""Database repository helpers for runtime project state and growth data."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime import AnalyticsEvent, LandingLead, RuntimeProject


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _normalized_project_state(project: dict[str, Any]) -> dict[str, Any]:
    state = copy.deepcopy(project)
    # Keep IDs as strings in state payload for API compatibility.
    state["id"] = str(state.get("id", ""))
    if state.get("user_id") is not None:
        state["user_id"] = str(state["user_id"])
    return state


def _project_from_row(row: RuntimeProject) -> dict[str, Any]:
    state = copy.deepcopy(row.state or {})
    state["id"] = str(row.id)
    state["user_id"] = str(row.user_id)
    state["title"] = row.title
    state["product_description"] = row.product_description
    state["status"] = row.status
    state["current_stage"] = row.current_stage
    state["error"] = row.error
    return state


async def get_runtime_project(
    session: AsyncSession,
    project_id: str,
) -> dict[str, Any] | None:
    normalized_id = _normalize_uuid(project_id)
    if normalized_id is None:
        return None
    row = await session.get(RuntimeProject, normalized_id)
    if not row:
        return None
    return _project_from_row(row)


async def list_runtime_projects(session: AsyncSession) -> list[dict[str, Any]]:
    stmt: Select[tuple[RuntimeProject]] = select(RuntimeProject).order_by(RuntimeProject.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return [_project_from_row(row) for row in rows]


async def upsert_runtime_project(session: AsyncSession, project: dict[str, Any]) -> None:
    project_id = _normalize_uuid(project.get("id"))
    if project_id is None:
        raise ValueError("Project id is required")

    row = await session.get(RuntimeProject, project_id)
    if row is None:
        row = RuntimeProject(
            id=project_id,
            user_id=_normalize_uuid(project.get("user_id")) or uuid.uuid4(),
            title=project.get("title") or "Untitled project",
            product_description=project.get("product_description") or "",
            status=project.get("status") or "parsing",
            current_stage=project.get("current_stage") or "parsing",
            error=project.get("error"),
            state=_normalized_project_state(project),
        )
        session.add(row)
    else:
        row.user_id = _normalize_uuid(project.get("user_id")) or row.user_id
        row.title = project.get("title") or row.title
        row.product_description = project.get("product_description") or row.product_description
        row.status = project.get("status") or row.status
        row.current_stage = project.get("current_stage") or row.current_stage
        row.error = project.get("error")
        row.state = _normalized_project_state(project)

    await session.flush()


async def append_progress_event(
    session: AsyncSession,
    project_id: str,
    event: dict[str, Any],
) -> None:
    row = await session.get(RuntimeProject, _normalize_uuid(project_id))
    if row is None:
        return
    state = copy.deepcopy(row.state or {})
    state.setdefault("progress_events", []).append(event)
    row.state = state
    await session.flush()


async def find_project_by_email_id(
    session: AsyncSession,
    email_id: str,
) -> tuple[dict[str, Any] | None, int | None]:
    projects = await list_runtime_projects(session)
    for project in projects:
        outreach = project.get("outreach_state") or {}
        for status in outreach.get("supplier_statuses", []):
            if status.get("email_id") == email_id:
                return project, status.get("supplier_index")
    return None, None


async def find_project_by_call_id(
    session: AsyncSession,
    call_id: str,
) -> tuple[dict[str, Any] | None, int | None]:
    projects = await list_runtime_projects(session)
    for project in projects:
        outreach = project.get("outreach_state") or {}
        for idx, call in enumerate(outreach.get("phone_calls", [])):
            if call.get("call_id") == call_id:
                return project, idx
    return None, None


async def recover_stale_running_projects(session: AsyncSession) -> int:
    projects = await list_runtime_projects(session)
    running = {"parsing", "clarifying", "discovering", "verifying", "comparing", "recommending"}
    recovered = 0

    for project in projects:
        if project.get("status") not in running:
            continue
        project["status"] = "failed"
        project["current_stage"] = "failed"
        project["error"] = "server_restart: project run interrupted by API restart"
        state = copy.deepcopy(project)
        state["recovery"] = {
            "reason": "server_restart",
            "recovered_at": datetime.now(timezone.utc).isoformat(),
        }
        project.update(state)
        await upsert_runtime_project(session, project)
        recovered += 1

    return recovered


async def upsert_landing_lead(
    session: AsyncSession,
    email: str,
    sourcing_note: str | None,
    source: str,
) -> tuple[str, bool]:
    normalized = email.strip().lower()
    stmt = select(LandingLead).where(LandingLead.email == normalized)
    existing = (await session.execute(stmt)).scalars().first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.last_seen_at = now
        if sourcing_note:
            existing.sourcing_note = sourcing_note
        if source:
            existing.source = source
        await session.flush()
        return str(existing.id), True

    lead = LandingLead(
        email=normalized,
        sourcing_note=sourcing_note,
        source=source,
        first_seen_at=now,
        last_seen_at=now,
    )
    session.add(lead)
    await session.flush()
    return str(lead.id), False


async def create_analytics_event(
    session: AsyncSession,
    event_name: str,
    session_id: str | None,
    path: str | None,
    project_id: str | None,
    payload: dict[str, Any] | None = None,
) -> str:
    row = AnalyticsEvent(
        event_name=event_name,
        session_id=session_id,
        path=path,
        project_id=_normalize_uuid(project_id),
        payload=payload or {},
    )
    session.add(row)
    await session.flush()
    return str(row.id)
