"""Project service — manages automotive procurement project lifecycle."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from automotive.agents.orchestrator import compile_graph
from automotive.api.v1.events import automotive_project_id, emit_activity
from automotive.models.project import AutomotiveProject, AutomotiveProjectEvent
from automotive.schemas.pipeline_state import ProcurementState

logger = logging.getLogger(__name__)

# In-memory fallback store for development without database
_in_memory_projects: dict[str, dict] = {}

# Whether we have a live database (set on first create)
_has_db: bool = False


async def create_project(
    db: AsyncSession | None,
    raw_request: str,
    user_id: str | None = None,
    org_id: str = "default",
    buyer_company: str = "",
    buyer_contact_name: str = "",
    buyer_contact_email: str = "",
) -> dict[str, Any]:
    """Create a new automotive procurement project and start the pipeline."""
    global _has_db
    project_id = str(uuid.uuid4())

    if db:
        _has_db = True
        project = AutomotiveProject(
            id=uuid.UUID(project_id),
            user_id=uuid.UUID(user_id) if user_id else None,
            org_id=org_id,
            raw_request=raw_request,
            buyer_company=buyer_company,
            buyer_contact_name=buyer_contact_name,
            buyer_contact_email=buyer_contact_email,
        )
        db.add(project)
        await db.flush()
    else:
        _in_memory_projects[project_id] = {
            "project_id": project_id,
            "raw_request": raw_request,
            "current_stage": "parse",
            "status": "running",
            "parsed_requirement": None,
            "discovery_result": None,
            "qualification_result": None,
            "comparison_matrix": None,
            "intelligence_reports": None,
            "rfq_result": None,
            "quote_ingestion": None,
            "approvals": {},
            "weight_profile": {},
            "buyer_company": buyer_company,
            "buyer_contact_name": buyer_contact_name,
            "buyer_contact_email": buyer_contact_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Start the pipeline asynchronously (uses its own DB session)
    import asyncio
    asyncio.create_task(
        _run_pipeline(project_id, raw_request, buyer_company, buyer_contact_name, buyer_contact_email)
    )

    return {
        "project_id": project_id,
        "status": "running",
        "current_stage": "parse",
    }


async def _run_pipeline(
    project_id: str,
    raw_request: str,
    buyer_company: str = "",
    buyer_contact_name: str = "",
    buyer_contact_email: str = "",
) -> None:
    """Execute the LangGraph pipeline for a project.

    Runs as a background task with its own DB session so it isn't
    tied to the lifecycle of the HTTP request that created the project.
    """
    # Set context var so agents can emit activity events
    automotive_project_id.set(project_id)

    emit_activity("pipeline", "start", f"Pipeline started for project {project_id[:8]}", project_id=project_id)

    graph = compile_graph()

    initial_state: ProcurementState = {
        "project_id": project_id,
        "org_id": "default",
        "created_by": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw_request": raw_request,
        "current_stage": "parse",
        "approvals": {},
        "human_overrides": {},
        "messages": [],
        "errors": [],
        "buyer_company": buyer_company,
        "buyer_contact_name": buyer_contact_name,
        "buyer_contact_email": buyer_contact_email,
    }

    config = {"configurable": {"thread_id": project_id}}

    try:
        emit_activity("parse", "start", "Parsing procurement requirements with AI...", project_id=project_id)
        # Run until first interrupt (HITL gate)
        await graph.ainvoke(initial_state, config)

        # Read full checkpoint state (reliable even after interrupt)
        snapshot = await graph.aget_state(config)
        state_values = snapshot.values if snapshot else {}
        logger.info(
            "State snapshot keys: %s, has parsed_requirement: %s",
            list(state_values.keys()) if isinstance(state_values, dict) else "N/A",
            "parsed_requirement" in state_values if isinstance(state_values, dict) else False,
        )

        await _persist_state(project_id, state_values)
        stage = state_values.get("current_stage", "unknown") if isinstance(state_values, dict) else "unknown"
        emit_activity(stage, "paused", f"Pipeline paused — awaiting approval at {stage}", project_id=project_id)
        logger.info("Pipeline paused at stage: %s for project %s", stage, project_id)
    except Exception as exc:
        logger.exception("Pipeline failed for project %s", project_id)
        emit_activity("pipeline", "error", f"Pipeline error: {exc}", project_id=project_id)
        await _persist_state(project_id, {"status": "error", "current_stage": "error"})


# Keys from LangGraph state that map directly to DB / in-memory project fields
_STATE_KEYS = {
    "current_stage", "parsed_requirement", "discovery_result",
    "qualification_result", "comparison_matrix", "intelligence_reports",
    "rfq_result", "quote_ingestion", "approvals", "weight_profile",
}


def _infer_status(stage: str | None) -> str:
    if stage == "error":
        return "error"
    if stage == "complete":
        return "complete"
    return "waiting_approval"


async def _persist_state(project_id: str, state: dict) -> None:
    """Persist pipeline state to both in-memory store and database.

    Creates its own DB session so it can be called from background tasks.
    """
    # Build the subset of fields to update
    updates: dict[str, Any] = {}
    for key in _STATE_KEYS:
        if key in state and state[key] is not None:
            updates[key] = state[key]
    updates["status"] = _infer_status(state.get("current_stage"))

    # Update in-memory store (for local dev / fallback)
    if project_id in _in_memory_projects:
        _in_memory_projects[project_id].update(updates)

    # Update database
    if _has_db:
        try:
            async with async_session_factory() as session:
                await session.execute(
                    update(AutomotiveProject)
                    .where(AutomotiveProject.id == uuid.UUID(project_id))
                    .values(**updates)
                )
                await session.commit()
                logger.info("Persisted state to DB for project %s (keys: %s)", project_id[:8], list(updates.keys()))
        except Exception:
            logger.exception("Failed to persist state to DB for project %s", project_id)


async def get_project(db: AsyncSession | None, project_id: str) -> dict[str, Any] | None:
    """Get a project by ID."""
    if db:
        result = await db.execute(
            select(AutomotiveProject).where(AutomotiveProject.id == uuid.UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if project:
            return {
                "project_id": str(project.id),
                "raw_request": project.raw_request,
                "current_stage": project.current_stage,
                "status": project.status,
                "parsed_requirement": project.parsed_requirement,
                "discovery_result": project.discovery_result,
                "qualification_result": project.qualification_result,
                "comparison_matrix": project.comparison_matrix,
                "intelligence_reports": project.intelligence_reports,
                "rfq_result": project.rfq_result,
                "quote_ingestion": project.quote_ingestion,
                "approvals": project.approvals,
                "weight_profile": project.weight_profile,
                "buyer_company": project.buyer_company,
                "created_at": project.created_at.isoformat(),
            }
    return _in_memory_projects.get(project_id)


async def list_projects(db: AsyncSession | None, user_id: str | None = None) -> list[dict]:
    """List all projects, optionally filtered by user."""
    if db:
        query = select(AutomotiveProject).order_by(AutomotiveProject.created_at.desc())
        if user_id:
            query = query.where(AutomotiveProject.user_id == uuid.UUID(user_id))
        result = await db.execute(query)
        projects = result.scalars().all()
        return [
            {
                "project_id": str(p.id),
                "raw_request": p.raw_request[:200],
                "current_stage": p.current_stage,
                "status": p.status,
                "buyer_company": p.buyer_company,
                "created_at": p.created_at.isoformat(),
            }
            for p in projects
        ]
    return list(_in_memory_projects.values())


async def approve_stage(
    db: AsyncSession | None,
    project_id: str,
    stage: str,
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Submit human approval for a pipeline stage gate.

    Resumes the LangGraph graph via Command(resume=...).
    """
    automotive_project_id.set(project_id)
    emit_activity(stage, "approved", f"Human approved stage: {stage}", project_id=project_id)

    graph = compile_graph()
    config = {"configurable": {"thread_id": project_id}}

    try:
        from langgraph.types import Command
        emit_activity(stage, "resuming", f"Resuming pipeline from {stage}...", project_id=project_id)
        await graph.ainvoke(Command(resume=decision), config)

        # Read the full checkpoint state
        snapshot = await graph.aget_state(config)
        state_values = snapshot.values if snapshot else {}
        logger.info("Resume snapshot keys: %s", list(state_values.keys()) if isinstance(state_values, dict) else "N/A")

        await _persist_state(project_id, state_values)
        new_stage = state_values.get("current_stage", "unknown") if isinstance(state_values, dict) else "unknown"
        emit_activity(new_stage, "paused", f"Pipeline advanced to {new_stage}", project_id=project_id)
        return {"status": "resumed", "current_stage": new_stage}
    except Exception as exc:
        logger.exception("Failed to resume pipeline for project %s at stage %s", project_id, stage)
        emit_activity(stage, "error", f"Resume failed: {exc}", project_id=project_id)
        return {"status": "error", "error": "Failed to resume pipeline"}
