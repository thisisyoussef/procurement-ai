"""Project store abstraction with database-first persistence and local fallback."""

from __future__ import annotations

import copy
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.models.runtime import AnalyticsEvent, LandingLead, RuntimeProject
from app.repositories import runtime_repository as repo

logger = logging.getLogger(__name__)
settings = get_settings()

_inmemory_projects: dict[str, dict[str, Any]] = {}
_inmemory_leads: dict[str, dict[str, Any]] = {}
_inmemory_events: list[dict[str, Any]] = []


class StoreUnavailableError(RuntimeError):
    """Raised when the configured persistence store cannot be reached."""


class BaseProjectStore(ABC):
    @abstractmethod
    async def create_project(self, project: dict[str, Any]) -> None: ...

    @abstractmethod
    async def get_project(self, project_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def save_project(self, project: dict[str, Any]) -> None: ...

    @abstractmethod
    async def list_projects(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def append_progress_event(self, project_id: str, event: dict[str, Any]) -> None: ...

    @abstractmethod
    async def find_project_by_email_id(self, email_id: str) -> tuple[dict[str, Any] | None, int | None]: ...

    @abstractmethod
    async def find_project_by_call_id(self, call_id: str) -> tuple[dict[str, Any] | None, int | None]: ...

    @abstractmethod
    async def upsert_lead(self, email: str, sourcing_note: str | None, source: str) -> tuple[str, bool]: ...

    @abstractmethod
    async def create_event(
        self,
        event_name: str,
        session_id: str | None,
        path: str | None,
        project_id: str | None,
        payload: dict[str, Any] | None = None,
    ) -> str: ...

    @abstractmethod
    async def recover_stale_runs(self) -> int: ...


class InMemoryProjectStore(BaseProjectStore):
    def __init__(self, projects: dict[str, dict[str, Any]]):
        self.projects = projects

    @staticmethod
    def _clone(value: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(value)

    async def create_project(self, project: dict[str, Any]) -> None:
        self.projects[project["id"]] = self._clone(project)

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        project = self.projects.get(project_id)
        return self._clone(project) if project else None

    async def save_project(self, project: dict[str, Any]) -> None:
        self.projects[project["id"]] = self._clone(project)

    async def list_projects(self) -> list[dict[str, Any]]:
        return [self._clone(project) for project in self.projects.values()]

    async def append_progress_event(self, project_id: str, event: dict[str, Any]) -> None:
        project = self.projects.get(project_id)
        if not project:
            return
        project.setdefault("progress_events", []).append(copy.deepcopy(event))

    async def find_project_by_email_id(self, email_id: str) -> tuple[dict[str, Any] | None, int | None]:
        for project in self.projects.values():
            outreach = project.get("outreach_state") or {}
            for status in outreach.get("supplier_statuses", []):
                if status.get("email_id") == email_id or email_id in (status.get("email_ids") or []):
                    return self._clone(project), status.get("supplier_index")
            monitor = outreach.get("communication_monitor") or {}
            for msg in monitor.get("messages", []):
                if msg.get("resend_email_id") == email_id:
                    return self._clone(project), msg.get("supplier_index")
        return None, None

    async def find_project_by_call_id(self, call_id: str) -> tuple[dict[str, Any] | None, int | None]:
        for project in self.projects.values():
            outreach = project.get("outreach_state") or {}
            for idx, call in enumerate(outreach.get("phone_calls", [])):
                if call.get("call_id") == call_id:
                    return self._clone(project), idx
        return None, None

    async def upsert_lead(self, email: str, sourcing_note: str | None, source: str) -> tuple[str, bool]:
        normalized = email.strip().lower()
        existing = _inmemory_leads.get(normalized)
        if existing:
            existing["last_seen_at"] = time.time()
            if sourcing_note:
                existing["sourcing_note"] = sourcing_note
            existing["source"] = source or existing.get("source")
            return existing["id"], True

        lead_id = str(uuid.uuid4())
        _inmemory_leads[normalized] = {
            "id": lead_id,
            "email": normalized,
            "sourcing_note": sourcing_note,
            "source": source,
            "first_seen_at": time.time(),
            "last_seen_at": time.time(),
        }
        return lead_id, False

    async def create_event(
        self,
        event_name: str,
        session_id: str | None,
        path: str | None,
        project_id: str | None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        _inmemory_events.append(
            {
                "id": event_id,
                "event_name": event_name,
                "session_id": session_id,
                "path": path,
                "project_id": project_id,
                "payload": payload or {},
            }
        )
        return event_id

    async def recover_stale_runs(self) -> int:
        running = {
            "parsing",
            "clarifying",
            "discovering",
            "verifying",
            "steering",
            "comparing",
            "recommending",
            "outreaching",
        }
        recovered = 0
        for project in self.projects.values():
            if project.get("status") not in running:
                continue
            project["status"] = "failed"
            project["current_stage"] = "failed"
            project["error"] = "server_restart: project run interrupted by API restart"
            project["recovery"] = {"reason": "server_restart"}
            recovered += 1
        return recovered


class DatabaseProjectStore(BaseProjectStore):
    _runtime_schema_ready: bool = False

    async def _ensure_runtime_schema(self) -> None:
        if self.__class__._runtime_schema_ready:
            return

        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: RuntimeProject.__table__.create(sync_conn, checkfirst=True))
            await conn.run_sync(lambda sync_conn: LandingLead.__table__.create(sync_conn, checkfirst=True))
            await conn.run_sync(lambda sync_conn: AnalyticsEvent.__table__.create(sync_conn, checkfirst=True))

        self.__class__._runtime_schema_ready = True
        logger.info("Ensured runtime persistence tables exist")

    async def _ping(self) -> None:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))

    async def create_project(self, project: dict[str, Any]) -> None:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            await repo.upsert_runtime_project(session, project)
            await session.commit()

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            return await repo.get_runtime_project(session, project_id)

    async def save_project(self, project: dict[str, Any]) -> None:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            await repo.upsert_runtime_project(session, project)
            await session.commit()

    async def list_projects(self) -> list[dict[str, Any]]:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            return await repo.list_runtime_projects(session)

    async def append_progress_event(self, project_id: str, event: dict[str, Any]) -> None:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            await repo.append_progress_event(session, project_id, event)
            await session.commit()

    async def find_project_by_email_id(self, email_id: str) -> tuple[dict[str, Any] | None, int | None]:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            return await repo.find_project_by_email_id(session, email_id)

    async def find_project_by_call_id(self, call_id: str) -> tuple[dict[str, Any] | None, int | None]:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            return await repo.find_project_by_call_id(session, call_id)

    async def upsert_lead(self, email: str, sourcing_note: str | None, source: str) -> tuple[str, bool]:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            lead_id, deduped = await repo.upsert_landing_lead(session, email, sourcing_note, source)
            await session.commit()
            return lead_id, deduped

    async def create_event(
        self,
        event_name: str,
        session_id: str | None,
        path: str | None,
        project_id: str | None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            event_id = await repo.create_analytics_event(
                session=session,
                event_name=event_name,
                session_id=session_id,
                path=path,
                project_id=project_id,
                payload=payload,
            )
            await session.commit()
            return event_id

    async def recover_stale_runs(self) -> int:
        await self._ensure_runtime_schema()
        async with async_session_factory() as session:
            recovered = await repo.recover_stale_running_projects(session)
            await session.commit()
            return recovered


class FallbackProjectStore(BaseProjectStore):
    def __init__(
        self,
        primary: DatabaseProjectStore,
        fallback: InMemoryProjectStore,
        allow_fallback: bool,
    ):
        self.primary = primary
        self.fallback = fallback
        self.allow_fallback = allow_fallback
        self._fallback_active = False
        self._warned = False

    async def _call(self, primary_call, fallback_call):
        if self._fallback_active:
            return await fallback_call()
        try:
            return await primary_call()
        except Exception as exc:  # noqa: BLE001
            if not self.allow_fallback:
                raise StoreUnavailableError(str(exc)) from exc
            self._fallback_active = True
            if not self._warned:
                self._warned = True
                logger.warning("Database project store unavailable, switching to in-memory fallback: %s", exc)
            return await fallback_call()

    async def create_project(self, project: dict[str, Any]) -> None:
        await self._call(
            lambda: self.primary.create_project(project),
            lambda: self.fallback.create_project(project),
        )

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        return await self._call(
            lambda: self.primary.get_project(project_id),
            lambda: self.fallback.get_project(project_id),
        )

    async def save_project(self, project: dict[str, Any]) -> None:
        await self._call(
            lambda: self.primary.save_project(project),
            lambda: self.fallback.save_project(project),
        )

    async def list_projects(self) -> list[dict[str, Any]]:
        return await self._call(
            self.primary.list_projects,
            self.fallback.list_projects,
        )

    async def append_progress_event(self, project_id: str, event: dict[str, Any]) -> None:
        await self._call(
            lambda: self.primary.append_progress_event(project_id, event),
            lambda: self.fallback.append_progress_event(project_id, event),
        )

    async def find_project_by_email_id(self, email_id: str) -> tuple[dict[str, Any] | None, int | None]:
        return await self._call(
            lambda: self.primary.find_project_by_email_id(email_id),
            lambda: self.fallback.find_project_by_email_id(email_id),
        )

    async def find_project_by_call_id(self, call_id: str) -> tuple[dict[str, Any] | None, int | None]:
        return await self._call(
            lambda: self.primary.find_project_by_call_id(call_id),
            lambda: self.fallback.find_project_by_call_id(call_id),
        )

    async def upsert_lead(self, email: str, sourcing_note: str | None, source: str) -> tuple[str, bool]:
        return await self._call(
            lambda: self.primary.upsert_lead(email, sourcing_note, source),
            lambda: self.fallback.upsert_lead(email, sourcing_note, source),
        )

    async def create_event(
        self,
        event_name: str,
        session_id: str | None,
        path: str | None,
        project_id: str | None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        return await self._call(
            lambda: self.primary.create_event(event_name, session_id, path, project_id, payload),
            lambda: self.fallback.create_event(event_name, session_id, path, project_id, payload),
        )

    async def recover_stale_runs(self) -> int:
        return await self._call(
            self.primary.recover_stale_runs,
            self.fallback.recover_stale_runs,
        )


_store_instance: BaseProjectStore | None = None


def get_project_store() -> BaseProjectStore:
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    memory = InMemoryProjectStore(_inmemory_projects)
    backend = (settings.project_store_backend or "database").lower()
    if backend == "inmemory":
        _store_instance = memory
        return _store_instance

    allow_fallback = bool(settings.project_store_fallback_inmemory and not settings.is_production)
    _store_instance = FallbackProjectStore(DatabaseProjectStore(), memory, allow_fallback=allow_fallback)
    return _store_instance


def get_legacy_project_dict() -> dict[str, dict[str, Any]]:
    """Compatibility accessor for legacy tests that seed the in-memory store."""
    return _inmemory_projects


def reset_project_store_for_tests() -> None:
    """Reset singleton + in-memory backing stores for deterministic tests."""
    global _store_instance
    _store_instance = None
    _inmemory_projects.clear()
    _inmemory_leads.clear()
    _inmemory_events.clear()
