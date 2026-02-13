"""Granular progress event system for the pipeline.

Writes progress events to the active project store. Persistence updates
are dispatched asynchronously so agent stages stay non-blocking.
"""

import asyncio
import logging
import time

from app.core.log_stream import current_project_id
from app.services.project_store import get_project_store

logger = logging.getLogger(__name__)

async def _persist_progress_event(project_id: str, event: dict) -> None:
    """Persist a progress event in the background."""
    store = get_project_store()
    try:
        await store.append_progress_event(project_id, event)
    except Exception:
        logger.debug("Skipping progress persistence for project %s", project_id, exc_info=True)


def emit_progress(
    stage: str,
    substep: str,
    detail: str,
    progress_pct: float | None = None,
) -> None:
    """Emit a granular progress event visible to the frontend.

    Args:
        stage: Pipeline stage (parsing, discovering, verifying, etc.)
        substep: Sub-step identifier (searching_google, resolving_intermediary, etc.)
        detail: Human-readable detail shown in UI
        progress_pct: Optional 0-100 progress within the current stage
    """
    project_id = current_project_id.get()
    if not project_id:
        return

    event = {
        "stage": stage,
        "substep": substep,
        "detail": detail,
        "progress_pct": progress_pct,
        "timestamp": time.time(),
    }

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_progress_event(project_id, event))
    except RuntimeError:
        # No running loop (e.g. sync context). Skip persistence.
        pass

    # Also log so it shows in the log stream
    logger.info("📊 [%s/%s] %s", stage, substep, detail)
