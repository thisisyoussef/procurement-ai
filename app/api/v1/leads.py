"""Landing lead capture endpoints."""

import re

from fastapi import APIRouter, HTTPException

from app.schemas.project import LeadCreateRequest
from app.services.project_store import StoreUnavailableError, get_project_store

router = APIRouter(prefix="/leads", tags=["leads"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("")
async def create_lead(request: LeadCreateRequest):
    normalized_email = request.email.strip().lower()
    if not EMAIL_REGEX.match(normalized_email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    store = get_project_store()
    try:
        lead_id, deduped = await store.upsert_lead(
            email=normalized_email,
            sourcing_note=request.sourcing_note,
            source=request.source,
        )
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc

    return {"ok": True, "lead_id": lead_id, "deduped": deduped}
