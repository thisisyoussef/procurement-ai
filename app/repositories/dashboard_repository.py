"""Repository helpers for dashboard summary/activity data."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import ProjectEvent
from app.models.runtime import RuntimeProject
from app.models.supplier import Supplier, SupplierInteraction


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _to_epoch(value: datetime | None) -> float | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


async def create_project_event(
    session: AsyncSession,
    *,
    user_id: str | uuid.UUID,
    project_id: str | uuid.UUID,
    event_type: str,
    title: str,
    description: str | None = None,
    priority: str = "info",
    phase: str | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    user_uuid = _normalize_uuid(user_id)
    project_uuid = _normalize_uuid(project_id)
    if user_uuid is None:
        raise ValueError("user_id is required")
    if project_uuid is None:
        raise ValueError("project_id is required")

    row = ProjectEvent(
        user_id=user_uuid,
        project_id=project_uuid,
        event_type=event_type,
        priority=priority,
        phase=phase,
        title=title,
        description=description,
        payload=payload or {},
    )
    session.add(row)
    await session.flush()
    return str(row.id)


async def list_project_events(
    session: AsyncSession,
    *,
    user_id: str | uuid.UUID,
    limit: int = 50,
    before: datetime | None = None,
) -> list[dict[str, Any]]:
    user_uuid = _normalize_uuid(user_id)
    if user_uuid is None:
        return []

    stmt: Select[tuple[ProjectEvent]] = (
        select(ProjectEvent)
        .where(ProjectEvent.user_id == user_uuid)
        .order_by(ProjectEvent.created_at.desc())
        .limit(max(1, min(limit, 200)))
    )

    if before is not None:
        stmt = stmt.where(ProjectEvent.created_at < before)

    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(row.id),
            "user_id": str(row.user_id),
            "project_id": str(row.project_id),
            "event_type": row.event_type,
            "priority": row.priority,
            "phase": row.phase,
            "title": row.title,
            "description": row.description,
            "payload": row.payload or {},
            "created_at": _to_epoch(row.created_at),
        }
        for row in rows
    ]


async def list_supplier_contacts_for_user(
    session: AsyncSession,
    *,
    user_id: str | uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    user_uuid = _normalize_uuid(user_id)
    if user_uuid is None:
        return []

    interaction_count = func.count(SupplierInteraction.id).label("interaction_count")
    project_count = func.count(func.distinct(SupplierInteraction.project_id)).label("project_count")
    last_interaction = func.max(SupplierInteraction.created_at).label("last_interaction_at")

    stmt = (
        select(
            Supplier,
            interaction_count,
            project_count,
            last_interaction,
        )
        .join(SupplierInteraction, SupplierInteraction.supplier_id == Supplier.id)
        .join(
            RuntimeProject,
            RuntimeProject.id == SupplierInteraction.project_id,
        )
        .where(RuntimeProject.user_id == user_uuid)
        .group_by(Supplier.id)
        .order_by(interaction_count.desc(), last_interaction.desc())
        .limit(max(1, min(limit, 200)))
    )

    rows = (await session.execute(stmt)).all()
    suppliers: list[dict[str, Any]] = []
    for supplier, interactions, projects, last_at in rows:
        suppliers.append(
            {
                "supplier_id": str(supplier.id),
                "name": supplier.name,
                "website": supplier.website,
                "email": supplier.email,
                "phone": supplier.phone,
                "city": supplier.city,
                "country": supplier.country,
                "interaction_count": int(interactions or 0),
                "project_count": int(projects or 0),
                "last_interaction_at": _to_epoch(last_at),
            }
        )
    return suppliers
