"""Dashboard endpoints for Tamkin home experience."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.api.v1.projects import _run_pipeline_task
from app.core.auth import AuthUser, get_current_auth_user
from app.schemas.dashboard import (
    DashboardActivityResponse,
    DashboardContactsResponse,
    DashboardProjectStartRequest,
    DashboardProjectStartResponse,
    DashboardSummaryResponse,
)
from app.services.dashboard_service import (
    get_dashboard_activity_for_user,
    get_dashboard_contacts_for_user,
    get_dashboard_summary_for_user,
)
from app.services.project_events import record_project_event
from app.services.project_store import StoreUnavailableError, get_project_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(current_user: AuthUser = Depends(get_current_auth_user)):
    try:
        return await get_dashboard_summary_for_user(
            user_id=current_user.user_id,
            full_name=current_user.full_name,
            email=current_user.email,
        )
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


@router.get("/activity", response_model=DashboardActivityResponse)
async def dashboard_activity(
    cursor: float | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    try:
        events, next_cursor = await get_dashboard_activity_for_user(
            user_id=current_user.user_id,
            limit=limit,
            cursor=cursor,
        )
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc
    return DashboardActivityResponse(events=events, next_cursor=next_cursor)


@router.get("/contacts", response_model=DashboardContactsResponse)
async def dashboard_contacts(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    try:
        return await get_dashboard_contacts_for_user(
            user_id=current_user.user_id,
            limit=limit,
        )
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


@router.post("/projects/start", response_model=DashboardProjectStartResponse)
async def start_project_from_dashboard(
    request: DashboardProjectStartRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    store = get_project_store()
    project_id = str(uuid.uuid4())
    title = (request.title or request.description[:80]).strip() or "New sourcing mission"

    project = {
        "id": project_id,
        "user_id": str(current_user.user_id),
        "owner_email": (current_user.email or "").strip().lower() or None,
        "title": title,
        "product_description": request.description.strip(),
        "auto_outreach": request.auto_outreach,
        "status": "parsing",
        "current_stage": "parsing",
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "chat_messages": [],
        "outreach_state": None,
        "progress_events": [],
        "clarifying_questions": None,
        "user_answers": None,
    }

    try:
        await store.create_project(project)
        await record_project_event(
            project,
            event_type="project_created",
            title="Project started",
            description=f"Started sourcing workflow for {title}.",
            priority="info",
            phase="brief",
            payload={"source": request.source},
        )
        await store.save_project(project)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create dashboard project")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        await store.create_event(
            event_name="dashboard_project_started",
            session_id=None,
            path="/dashboard",
            project_id=project_id,
            payload={"source": request.source},
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to persist dashboard_project_started analytics event", exc_info=True)

    background_tasks.add_task(_run_pipeline_task, project_id, request.description.strip())

    return DashboardProjectStartResponse(
        project_id=project_id,
        status="started",
        redirect_path=f"/product?projectId={project_id}&entry={request.source}",
    )
