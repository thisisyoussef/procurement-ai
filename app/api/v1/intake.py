"""Tamkin landing intake endpoints."""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.v1.projects import create_project
from app.schemas.project import IntakeStartRequest, ProjectCreateRequest
from app.services.project_store import StoreUnavailableError, get_project_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("/start")
async def start_intake(request: IntakeStartRequest, background_tasks: BackgroundTasks):
    """Create a project from landing intake and return a product redirect path."""
    title = " ".join(request.message.strip().split())[:80] or "New sourcing mission"
    project_request = ProjectCreateRequest(
        title=title,
        product_description=request.message.strip(),
    )

    result = await create_project(project_request, background_tasks)
    project_id = result["project_id"]

    store = get_project_store()
    try:
        await store.create_event(
            event_name="hero_intake_started",
            session_id=request.session_id,
            path="/",
            project_id=project_id,
            payload={"source": request.source},
        )
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc
    except Exception:
        logger.warning("Failed to persist intake telemetry event", exc_info=True)

    return {
        "project_id": project_id,
        "status": "started",
        "redirect_path": f"/product?projectId={project_id}&entry={request.source}",
    }

