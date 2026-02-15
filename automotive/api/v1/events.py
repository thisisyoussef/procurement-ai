"""SSE endpoint for streaming live project activity events."""

import asyncio
import json
import logging
import time
from collections import defaultdict
from contextvars import ContextVar
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["automotive-events"])
logger = logging.getLogger(__name__)

# ── Event infrastructure ──

# Context var so agents can emit events without passing project_id everywhere
automotive_project_id: ContextVar[str | None] = ContextVar(
    "automotive_project_id", default=None
)

# Per-project event log + live subscriber queues
_event_log: dict[str, list[dict]] = defaultdict(list)
_event_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

MAX_EVENTS_PER_PROJECT = 500


def emit_activity(
    stage: str,
    action: str,
    detail: str,
    *,
    project_id: str | None = None,
    meta: dict | None = None,
) -> None:
    """Emit a live activity event for the automotive pipeline.

    Call from any agent/tool/service. If project_id is not passed,
    it reads from the context var set by the pipeline runner.
    """
    pid = project_id or automotive_project_id.get()
    if not pid:
        return

    event = {
        "ts": time.time(),
        "time": time.strftime("%H:%M:%S", time.localtime()),
        "stage": stage,
        "action": action,
        "detail": detail,
    }
    if meta:
        event["meta"] = meta

    log = _event_log[pid]
    log.append(event)
    if len(log) > MAX_EVENTS_PER_PROJECT:
        _event_log[pid] = log[-MAX_EVENTS_PER_PROJECT:]

    for q in _event_queues.get(pid, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


def get_activity_log(project_id: str) -> list[dict]:
    return list(_event_log.get(project_id, []))


async def _subscribe(project_id: str) -> AsyncGenerator[str, None]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _event_queues[project_id].append(queue)

    try:
        # Replay existing events
        for entry in _event_log.get(project_id, []):
            yield f"data: {json.dumps(entry)}\n\n"

        # Stream new events
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(entry)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        _event_queues[project_id].remove(queue)


# ── HTTP endpoints ──


@router.get("/projects/{project_id}/events")
async def get_project_events(project_id: str) -> list[dict]:
    """Get all activity events for a project."""
    return get_activity_log(project_id)


@router.get("/projects/{project_id}/events/stream")
async def stream_project_events(project_id: str):
    """SSE stream of live activity events for a project."""
    return StreamingResponse(
        _subscribe(project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
