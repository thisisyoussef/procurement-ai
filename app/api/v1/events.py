"""First-party telemetry event endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.project import AnalyticsEventRequest
from app.services.project_store import StoreUnavailableError, get_project_store

router = APIRouter(prefix="/events", tags=["events"])


@router.post("")
async def create_event(request: AnalyticsEventRequest):
    store = get_project_store()
    try:
        event_id = await store.create_event(
            event_name=request.event_name,
            session_id=request.session_id,
            path=request.path,
            project_id=request.project_id,
            payload=request.payload,
        )
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc

    return {"ok": True, "event_id": event_id}

