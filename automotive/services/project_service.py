"""Project service — manages automotive procurement project lifecycle."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from automotive.agents.orchestrator import compile_graph
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
            "id": project_id,
            "raw_request": raw_request,
            "current_stage": "parse",
            "status": "running",
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
        # Run until first interrupt (HITL gate)
        result = await graph.ainvoke(initial_state, config)
        _update_project_state(project_id, result, db)
        logger.info("Pipeline paused at stage: %s for project %s", result.get("current_stage"), project_id)
    except Exception:
        logger.exception("Pipeline failed for project %s", project_id)
        _update_project_state(project_id, {"status": "error", "current_stage": "error"}, db)


def _update_project_state(project_id: str, state: dict, db: AsyncSession | None) -> None:
    """Update project state in memory (DB update happens via the session)."""
    if project_id in _in_memory_projects:
        _in_memory_projects[project_id].update(state)


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
    graph = compile_graph()
    config = {"configurable": {"thread_id": project_id}}

    try:
        from langgraph.types import Command
        result = await graph.ainvoke(Command(resume=decision), config)
        _update_project_state(project_id, result, db)
        return {"status": "resumed", "current_stage": result.get("current_stage")}
    except Exception:
        logger.exception("Failed to resume pipeline for project %s at stage %s", project_id, stage)
        return {"status": "error", "error": "Failed to resume pipeline"}
