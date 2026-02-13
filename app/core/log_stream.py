"""Per-project log streaming infrastructure.

Provides a custom logging handler that captures log messages per-project
and an SSE endpoint generator for streaming them to the frontend.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from contextvars import ContextVar
from typing import AsyncGenerator

# Context var to track which project is currently executing
current_project_id: ContextVar[str | None] = ContextVar("current_project_id", default=None)

# Per-project log storage: project_id -> list of log entries
_project_logs: dict[str, list[dict]] = defaultdict(list)

# Per-project queues for SSE push: project_id -> list of asyncio.Queue
_project_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


class ProjectLogHandler(logging.Handler):
    """Logging handler that captures logs for the current project."""

    def emit(self, record: logging.LogRecord) -> None:
        project_id = current_project_id.get()
        if not project_id:
            return

        entry = {
            "ts": time.time(),
            "time": time.strftime("%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name.replace("app.", ""),
            "message": record.getMessage(),
        }

        # Store in project log history
        _project_logs[project_id].append(entry)

        # Push to any listening SSE queues
        for q in _project_queues.get(project_id, []):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass  # Drop if consumer is too slow


def install_project_log_handler():
    """Install the project log handler on the root 'app' logger."""
    handler = ProjectLogHandler()
    handler.setLevel(logging.DEBUG)
    app_logger = logging.getLogger("app")
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.DEBUG)


def get_project_logs(project_id: str) -> list[dict]:
    """Get all stored logs for a project."""
    return _project_logs.get(project_id, [])


def clear_project_logs(project_id: str) -> None:
    """Clear stored logs for a project."""
    _project_logs.pop(project_id, None)


async def subscribe_to_logs(project_id: str) -> AsyncGenerator[str, None]:
    """
    SSE generator — yields log entries as they arrive.

    Usage in FastAPI:
        return StreamingResponse(subscribe_to_logs(pid), media_type="text/event-stream")
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _project_queues[project_id].append(queue)

    try:
        # First, send all existing logs as a batch
        for entry in _project_logs.get(project_id, []):
            yield f"data: {json.dumps(entry)}\n\n"

        # Then stream new ones
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(entry)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive to prevent connection timeout
                yield ": keepalive\n\n"
    finally:
        _project_queues[project_id].remove(queue)
