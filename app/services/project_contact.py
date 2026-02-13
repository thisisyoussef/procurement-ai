"""Helpers to resolve project owner contact details."""

from __future__ import annotations

import logging

from app.core.database import async_session_factory
from app.repositories.user_repository import get_user_by_id

logger = logging.getLogger(__name__)


async def resolve_project_owner_email(project: dict) -> str | None:
    owner_email = (project.get("owner_email") or "").strip().lower()
    if owner_email:
        return owner_email

    user_id = project.get("user_id")
    if not user_id:
        return None

    try:
        async with async_session_factory() as session:
            user = await get_user_by_id(session, str(user_id))
    except Exception:  # noqa: BLE001
        logger.warning("Failed to resolve owner email for project %s", project.get("id"), exc_info=True)
        return None

    if not user or not user.email:
        return None

    owner_email = user.email.strip().lower()
    if owner_email:
        project["owner_email"] = owner_email
    return owner_email or None
