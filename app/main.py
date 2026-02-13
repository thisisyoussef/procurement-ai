"""FastAPI application entry point."""

import logging
import os
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.log_stream import install_project_log_handler
from app.services.project_store import StoreUnavailableError, get_project_store

# Configure logging so errors show in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Install the per-project log handler so logs stream to the frontend
install_project_log_handler()

settings = get_settings()


def _parse_cors_origins(raw_origins: str) -> List[str]:
    return [
        origin.strip()
        for origin in (raw_origins or "").split(",")
        if origin.strip()
    ]


cors_origins = {
    settings.frontend_url,
    "http://localhost:3000",
    "http://localhost:5173",
}
cors_origins.update(_parse_cors_origins(os.getenv("CORS_ALLOW_ORIGINS", "")))
cors_origin_regex = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX",
    r"https://.*\.up\.railway\.app",
)

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Find the right people to make your stuff. Manage them like a pro.",
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(cors_origins),
    allow_origin_regex=cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler — returns details instead of bare 500
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {str(exc)}"},
    )


# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "app": settings.app_title,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.on_event("startup")
async def recover_stale_project_runs():
    """
    Mark any in-flight project runs as recoverable failures after process restart.

    This prevents projects from being stuck in a running stage if the API restarts
    while background tasks were executing.
    """
    try:
        store = get_project_store()
        recovered = await store.recover_stale_runs()
        if recovered:
            logger.info("Recovered %d stale project run(s) after startup", recovered)
    except StoreUnavailableError as exc:
        logger.warning("Project store unavailable during startup recovery: %s", exc)
    except Exception:
        logger.exception("Unexpected failure during startup stale-run recovery")
