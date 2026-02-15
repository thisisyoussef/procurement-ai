"""Aggregate all automotive v1 API routes."""

from fastapi import APIRouter

from automotive.api.v1.events import router as events_router
from automotive.api.v1.generate import router as generate_router
from automotive.api.v1.projects import router as projects_router
from automotive.api.v1.webhooks import router as webhooks_router

automotive_api_router = APIRouter(prefix="/api/v1/automotive")
automotive_api_router.include_router(projects_router)
automotive_api_router.include_router(webhooks_router)
automotive_api_router.include_router(events_router)
automotive_api_router.include_router(generate_router)
