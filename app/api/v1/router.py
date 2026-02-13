"""Aggregate all v1 API routes."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.events import router as events_router
from app.api.v1.intake import router as intake_router
from app.api.v1.leads import router as leads_router
from app.api.v1.outreach import router as outreach_router
from app.api.v1.phone import router as phone_router
from app.api.v1.projects import router as projects_router
from app.api.v1.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(intake_router)
api_router.include_router(leads_router)
api_router.include_router(events_router)
api_router.include_router(chat_router)
api_router.include_router(outreach_router)
api_router.include_router(phone_router)
api_router.include_router(webhooks_router, prefix="/webhooks")
