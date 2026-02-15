"""Project service — manages automotive procurement project lifecycle."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from automotive.agents.orchestrator import compile_graph
from automotive.api.v1.events import automotive_project_id, emit_activity
from automotive.models.project import AutomotiveProject, AutomotiveProjectEvent
from automotive.schemas.pipeline_state import ProcurementState

logger = logging.getLogger(__name__)

# In-memory fallback store for development without database
_in_memory_projects: dict[str, dict] = {}


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
    project_id = str(uuid.uuid4())

    if db:
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

    # Start the pipeline asynchronously
    import asyncio
    asyncio.create_task(_run_pipeline(project_id, raw_request, db, buyer_company, buyer_contact_name, buyer_contact_email))

    return {
        "project_id": project_id,
        "status": "running",
        "current_stage": "parse",
    }


async def _run_pipeline(
    project_id: str,
    raw_request: str,
    db: AsyncSession | None,
    buyer_company: str = "",
    buyer_contact_name: str = "",
    buyer_contact_email: str = "",
) -> None:
    """Execute the LangGraph pipeline for a project.

    In production with PostgresSaver, the graph persists state and
    pauses at HITL gates. For MVP, we run without interrupts.
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
        result = await graph.ainvoke(initial_state, config)
        logger.info("ainvoke returned type=%s, keys=%s", type(result).__name__, list(result.keys()) if isinstance(result, dict) else "N/A")

        # ainvoke returns the state snapshot; however when an interrupt fires,
        # the returned dict may be partial.  Always read the full checkpoint.
        snapshot = await graph.aget_state(config)
        state_values = snapshot.values if snapshot else {}
        logger.info(
            "State snapshot keys: %s, has parsed_requirement: %s",
            list(state_values.keys()) if isinstance(state_values, dict) else "N/A",
            "parsed_requirement" in state_values if isinstance(state_values, dict) else False,
        )

        _update_project_state(project_id, state_values, db)
        stage = state_values.get("current_stage", "unknown") if isinstance(state_values, dict) else "unknown"
        emit_activity(stage, "paused", f"Pipeline paused — awaiting approval at {stage}", project_id=project_id)
        logger.info("Pipeline paused at stage: %s for project %s", stage, project_id)
    except Exception as exc:
        logger.exception("Pipeline failed for project %s", project_id)
        emit_activity("pipeline", "error", f"Pipeline error: {exc}", project_id=project_id)
        _update_project_state(project_id, {"status": "error", "current_stage": "error"}, db)


# Keys from LangGraph state that map directly to project fields
_STATE_KEYS = {
    "current_stage", "parsed_requirement", "discovery_result",
    "qualification_result", "comparison_matrix", "intelligence_reports",
    "rfq_result", "quote_ingestion", "approvals", "weight_profile",
}


def _update_project_state(project_id: str, state: dict, db: AsyncSession | None) -> None:
    """Update project state in memory from a LangGraph result dict.

    Only copies recognised keys so that internal LangGraph bookkeeping
    (messages, errors, human_overrides, etc.) doesn't leak into the
    project record returned by the API.
    """
    if project_id not in _in_memory_projects:
        return

    proj = _in_memory_projects[project_id]
    for key in _STATE_KEYS:
        if key in state and state[key] is not None:
            proj[key] = state[key]

    # Infer status from stage
    stage = state.get("current_stage", proj.get("current_stage"))
    if stage == "error":
        proj["status"] = "error"
    elif stage == "complete":
        proj["status"] = "complete"
    else:
        proj["status"] = "waiting_approval"


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

    In production, this resumes the LangGraph graph via Command(resume=...).
    """
    automotive_project_id.set(project_id)
    emit_activity(stage, "approved", f"Human approved stage: {stage}", project_id=project_id)

    graph = compile_graph()
    config = {"configurable": {"thread_id": project_id}}

    try:
        from langgraph.types import Command
        emit_activity(stage, "resuming", f"Resuming pipeline from {stage}...", project_id=project_id)
        result = await graph.ainvoke(Command(resume=decision), config)

        # Read the full checkpoint state (more reliable than ainvoke return)
        snapshot = await graph.aget_state(config)
        state_values = snapshot.values if snapshot else result
        logger.info("Resume snapshot keys: %s", list(state_values.keys()) if isinstance(state_values, dict) else "N/A")

        _update_project_state(project_id, state_values, db)
        new_stage = state_values.get("current_stage", "unknown") if isinstance(state_values, dict) else "unknown"
        emit_activity(new_stage, "paused", f"Pipeline advanced to {new_stage}", project_id=project_id)
        return {"status": "resumed", "current_stage": new_stage}
    except Exception as exc:
        logger.exception("Failed to resume pipeline for project %s at stage %s", project_id, stage)
        emit_activity(stage, "error", f"Resume failed: {exc}", project_id=project_id)
        return {"status": "error", "error": "Failed to resume pipeline"}
