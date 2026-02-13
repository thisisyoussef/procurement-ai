"""Granular progress event system for the pipeline.

Writes progress events directly to the in-memory project dict so the
frontend picks them up on the next status poll (every 1 second).
No additional SSE channel required.
"""

import logging
import time

from app.core.log_stream import current_project_id

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency — projects.py imports from us
_projects_ref = None


def _get_projects() -> dict:
    global _projects_ref
    if _projects_ref is None:
        from app.api.v1.projects import _projects
        _projects_ref = _projects
    return _projects_ref


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

    projects = _get_projects()
    project = projects.get(project_id)
    if project:
        project.setdefault("progress_events", []).append(event)

    # Also log so it shows in the log stream
    logger.info("📊 [%s/%s] %s", stage, substep, detail)
