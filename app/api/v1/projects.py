"""Sourcing project API endpoints.

Supports:
- Pipeline creation and status polling
- Clarifying question pause/resume flow
- Progress event syncing for granular UI updates
"""

import logging
import time
import traceback
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import (
    compare_node,
    discover_node,
    parse_node,
    recommend_node,
    outreach_node,
    run_pipeline,
    verify_node,
    GraphState,
)
from app.core.auth import AuthUser, get_current_auth_user
from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.core.log_stream import current_project_id, get_project_logs, subscribe_to_logs
from app.schemas.agent_state import (
    ChatMessage,
    ComparisonResult,
    DiscoveryResults,
    OutreachState,
    ParsedRequirements,
    PipelineStage,
    RecommendationResult,
    VerificationResults,
)
from app.schemas.project import (
    ClarifyingAnswerRequest,
    PipelineStatusResponse,
    ProjectCreateRequest,
)
from app.services.project_store import (
    StoreUnavailableError,
    get_legacy_project_dict,
    get_project_store,
)
from app.services.project_events import record_project_event
from app.services.supplier_memory import (
    persist_discovered_suppliers,
    persist_verification_feedback,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/projects", tags=["projects"])

# Legacy compatibility for tests still importing this symbol.
_projects = get_legacy_project_dict()

ACTIVE_PIPELINE_STATUSES = {
    "parsing",
    "clarifying",
    "discovering",
    "verifying",
    "comparing",
    "recommending",
    "outreaching",
}

_STAGE_PHASE = {
    "parsing": "brief",
    "clarifying": "brief",
    "discovering": "search",
    "verifying": "search",
    "comparing": "compare",
    "recommending": "compare",
    "outreaching": "outreach",
    "complete": "order",
    "failed": "brief",
    "canceled": "brief",
}


def _stage_title(stage_name: str) -> str:
    titles = {
        "parsing": "Parsing requirements",
        "discovering": "Searching suppliers",
        "verifying": "Verifying suppliers",
        "comparing": "Comparing options",
        "recommending": "Generating recommendation",
        "outreaching": "Running outreach",
    }
    return titles.get(stage_name, stage_name.replace("_", " ").title())


async def _get_project_or_404(project_id: str) -> dict:
    store = get_project_store()
    try:
        project = await store.get_project(project_id)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _enforce_project_ownership(project: dict, current_user: AuthUser) -> None:
    if str(project.get("user_id")) != str(current_user.user_id):
        raise HTTPException(status_code=403, detail="Forbidden")


async def _save_project(project: dict) -> None:
    store = get_project_store()
    try:
        await store.save_project(project)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


async def _create_project(project: dict) -> None:
    store = get_project_store()
    try:
        await store.create_project(project)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


def _is_canceled(project: dict | None) -> bool:
    if not project:
        return False
    return project.get("status") == "canceled" or project.get("current_stage") == "canceled"


async def _should_stop_for_cancellation(store, project_id: str) -> tuple[bool, dict | None]:
    try:
        latest = await store.get_project(project_id)
    except Exception:
        logger.exception("Cancellation check failed for project %s", project_id)
        return True, None

    if not latest:
        logger.info("Stopping pipeline for missing project %s", project_id)
        return True, None

    if _is_canceled(latest):
        logger.info("Pipeline stop requested: project %s is canceled", project_id)
        return True, latest

    return False, latest


@router.post("")
async def create_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """
    Create a new sourcing project and start the AI pipeline.

    The pipeline runs in the background. Poll GET /projects/{id}/status
    to check progress.
    """
    try:
        project_id = str(uuid.uuid4())
        user_id = str(current_user.user_id)

        project = {
            "id": project_id,
            "user_id": user_id,
            "owner_email": (current_user.email or "").strip().lower() or None,
            "title": request.title,
            "product_description": request.product_description,
            "auto_outreach": request.auto_outreach,
            "status": "parsing",
            "current_stage": "parsing",
            "error": None,
            "parsed_requirements": None,
            "discovery_results": None,
            "verification_results": None,
            "comparison_result": None,
            "recommendation_result": None,
            "chat_messages": [],
            "outreach_state": None,
            "progress_events": [],
            "clarifying_questions": None,
            "user_answers": None,
        }

        await _create_project(project)
        await record_project_event(
            project,
            event_type="project_created",
            title="Project started",
            description=f"Started sourcing workflow for {request.title}.",
            priority="info",
            phase="brief",
            payload={"source": "product_form"},
        )
        await _save_project(project)

        # Run pipeline in background
        background_tasks.add_task(_run_pipeline_task, project_id, request.product_description)

        return {"project_id": project_id, "status": "started"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create project")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}\n{traceback.format_exc()}") from e


def _sync_state_to_project(project: dict, state: GraphState) -> None:
    """Push the current graph state into the project dict so polling picks it up."""
    project["current_stage"] = state.get("current_stage", project["current_stage"])
    project["status"] = state.get("current_stage", project["status"])
    project["error"] = state.get("error")
    if state.get("parsed_requirements"):
        project["parsed_requirements"] = state["parsed_requirements"]
    if state.get("discovery_results"):
        project["discovery_results"] = state["discovery_results"]
    if state.get("verification_results"):
        project["verification_results"] = state["verification_results"]
    if state.get("comparison_result"):
        project["comparison_result"] = state["comparison_result"]
    if state.get("recommendation_result"):
        project["recommendation_result"] = state["recommendation_result"]
    # Sync auto-outreach results from the pipeline outreach_node
    outreach_result = state.get("outreach_result")
    if outreach_result and not outreach_result.get("skipped") and not outreach_result.get("error"):
        project["outreach_state"] = outreach_result


async def _run_pipeline_task(project_id: str, description: str):
    """Background task that runs the pipeline step-by-step, updating project after each stage.

    After parsing, checks for clarifying questions. If found, pauses the pipeline
    (status = "clarifying") so the user can answer before discovery begins.
    """
    current_project_id.set(project_id)

    store = get_project_store()
    try:
        project = await store.get_project(project_id)
    except Exception:
        logger.exception("Pipeline start failed: project store unavailable")
        return

    if not project:
        return

    if _is_canceled(project):
        logger.info("Project %s is canceled before pipeline start", project_id)
        return

    state: GraphState = {
        "raw_description": description,
        "current_stage": PipelineStage.PARSING.value,
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "outreach_result": None,
        "progress_events": [],
        "user_answers": None,
        "auto_outreach_enabled": bool(project.get("auto_outreach")),
    }

    steps = [
        ("parsing", parse_node),
        ("discovering", discover_node),
        ("verifying", verify_node),
        ("comparing", compare_node),
        ("recommending", recommend_node),
    ]

    # Add outreach step if auto_outreach is enabled
    if project.get("auto_outreach"):
        steps.append(("outreaching", outreach_node))

    try:
        logger.info("Starting pipeline for project %s (auto_outreach=%s)", project_id, project.get("auto_outreach"))

        for stage_name, step_fn in steps:
            should_stop, latest_project = await _should_stop_for_cancellation(store, project_id)
            if should_stop:
                return
            project = latest_project or project

            project["current_stage"] = stage_name
            project["status"] = stage_name
            await record_project_event(
                project,
                event_type="stage_started",
                title=_stage_title(stage_name),
                description=f"Tamkin started {stage_name.replace('_', ' ')}.",
                priority="info",
                phase=_STAGE_PHASE.get(stage_name),
                payload={"stage": stage_name},
            )
            await store.save_project(project)

            state = await step_fn(state)

            should_stop, latest_project = await _should_stop_for_cancellation(store, project_id)
            if should_stop:
                return
            project = latest_project or project

            _sync_state_to_project(project, state)

            if stage_name == "discovering" and project.get("discovery_results"):
                persisted = await persist_discovered_suppliers(project_id, project.get("discovery_results"))
                if persisted:
                    project["discovery_results"] = persisted
            if stage_name == "verifying" and project.get("verification_results"):
                persisted_discovery = await persist_verification_feedback(
                    project_id=project_id,
                    discovery_results=project.get("discovery_results"),
                    verification_results=project.get("verification_results"),
                )
                if persisted_discovery:
                    project["discovery_results"] = persisted_discovery

            await record_project_event(
                project,
                event_type="stage_completed",
                title=f"{_stage_title(stage_name)} complete",
                description=f"Tamkin completed {stage_name.replace('_', ' ')}.",
                priority="info",
                phase=_STAGE_PHASE.get(stage_name),
                payload={"stage": stage_name},
            )
            await store.save_project(project)

            if state.get("error"):
                logger.error("Pipeline stopped at %s: %s", stage_name, state["error"][:200])
                await record_project_event(
                    project,
                    event_type="project_failed",
                    title="Pipeline failed",
                    description=state["error"][:300],
                    priority="high",
                    phase=_STAGE_PHASE.get(stage_name),
                    payload={"stage": stage_name},
                )
                await store.save_project(project)
                break

            if stage_name == "parsing":
                reqs = state.get("parsed_requirements") or {}
                questions = reqs.get("clarifying_questions", [])
                if questions:
                    project["status"] = "clarifying"
                    project["current_stage"] = "clarifying"
                    project["clarifying_questions"] = questions
                    await record_project_event(
                        project,
                        event_type="clarifying_required",
                        title="Need a few clarifications",
                        description=f"{len(questions)} clarification questions need answers.",
                        priority="high",
                        phase="brief",
                        payload={"question_count": len(questions)},
                    )
                    await store.save_project(project)
                    logger.info(
                        "Pipeline paused for %d clarifying questions (project %s)",
                        len(questions),
                        project_id,
                    )
                    return

        await record_project_event(
            project,
            event_type="project_completed",
            title="Pipeline complete",
            description="Discovery, verification, and recommendation are ready.",
            priority="info",
            phase=_STAGE_PHASE.get(project.get("current_stage")),
        )
        await store.save_project(project)
        logger.info("Pipeline completed for project %s, stage=%s", project_id, project["current_stage"])

    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline failed for project %s", project_id)
        project["status"] = "failed"
        project["current_stage"] = "failed"
        project["error"] = f"{str(e)}\n{traceback.format_exc()}"
        try:
            await record_project_event(
                project,
                event_type="project_failed",
                title="Pipeline failed",
                description=str(e),
                priority="high",
                phase="brief",
            )
            await store.save_project(project)
        except Exception:
            logger.exception("Failed to persist pipeline failure state")


async def _resume_pipeline_task(project_id: str):
    """Resume a paused pipeline from the discover stage onward."""
    current_project_id.set(project_id)

    store = get_project_store()
    try:
        project = await store.get_project(project_id)
    except Exception:
        logger.exception("Resume failed: project store unavailable")
        return

    if not project:
        return

    if _is_canceled(project):
        logger.info("Project %s is canceled before resume", project_id)
        return

    state: GraphState = {
        "raw_description": project.get("product_description", ""),
        "current_stage": PipelineStage.DISCOVERING.value,
        "error": None,
        "parsed_requirements": project.get("parsed_requirements"),
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "progress_events": project.get("progress_events", []),
        "user_answers": project.get("user_answers"),
    }

    steps = [
        ("discovering", discover_node),
        ("verifying", verify_node),
        ("comparing", compare_node),
        ("recommending", recommend_node),
    ]

    try:
        logger.info("Resuming pipeline for project %s from discover", project_id)

        for stage_name, step_fn in steps:
            should_stop, latest_project = await _should_stop_for_cancellation(store, project_id)
            if should_stop:
                return
            project = latest_project or project

            project["current_stage"] = stage_name
            project["status"] = stage_name
            await record_project_event(
                project,
                event_type="stage_started",
                title=_stage_title(stage_name),
                description=f"Tamkin resumed and started {stage_name.replace('_', ' ')}.",
                priority="info",
                phase=_STAGE_PHASE.get(stage_name),
                payload={"stage": stage_name, "resume": True},
            )
            await store.save_project(project)

            state = await step_fn(state)

            should_stop, latest_project = await _should_stop_for_cancellation(store, project_id)
            if should_stop:
                return
            project = latest_project or project

            _sync_state_to_project(project, state)

            if stage_name == "discovering" and project.get("discovery_results"):
                persisted = await persist_discovered_suppliers(project_id, project.get("discovery_results"))
                if persisted:
                    project["discovery_results"] = persisted
            if stage_name == "verifying" and project.get("verification_results"):
                persisted_discovery = await persist_verification_feedback(
                    project_id=project_id,
                    discovery_results=project.get("discovery_results"),
                    verification_results=project.get("verification_results"),
                )
                if persisted_discovery:
                    project["discovery_results"] = persisted_discovery

            await record_project_event(
                project,
                event_type="stage_completed",
                title=f"{_stage_title(stage_name)} complete",
                description=f"Tamkin completed {stage_name.replace('_', ' ')}.",
                priority="info",
                phase=_STAGE_PHASE.get(stage_name),
                payload={"stage": stage_name, "resume": True},
            )
            await store.save_project(project)

            if state.get("error"):
                logger.error("Pipeline stopped at %s: %s", stage_name, state["error"][:200])
                await record_project_event(
                    project,
                    event_type="project_failed",
                    title="Pipeline failed",
                    description=state["error"][:300],
                    priority="high",
                    phase=_STAGE_PHASE.get(stage_name),
                    payload={"stage": stage_name},
                )
                await store.save_project(project)
                break

        await record_project_event(
            project,
            event_type="project_completed",
            title="Pipeline complete",
            description="Discovery, verification, and recommendation are ready.",
            priority="info",
            phase=_STAGE_PHASE.get(project.get("current_stage")),
        )
        await store.save_project(project)
        logger.info("Pipeline completed for project %s, stage=%s", project_id, project["current_stage"])

    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline failed for project %s", project_id)
        project["status"] = "failed"
        project["current_stage"] = "failed"
        project["error"] = f"{str(e)}\n{traceback.format_exc()}"
        try:
            await record_project_event(
                project,
                event_type="project_failed",
                title="Pipeline failed",
                description=str(e),
                priority="high",
                phase="brief",
            )
            await store.save_project(project)
        except Exception:
            logger.exception("Failed to persist resumed pipeline failure state")


@router.get("/{project_id}/status", response_model=PipelineStatusResponse)
async def get_project_status(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Get the current status and results of a sourcing project pipeline."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)

    return PipelineStatusResponse(
        project_id=uuid.UUID(project["id"]),
        status=project["status"],
        current_stage=project["current_stage"],
        error=project.get("error"),
        parsed_requirements=(
            ParsedRequirements(**project["parsed_requirements"])
            if project.get("parsed_requirements")
            else None
        ),
        discovery_results=(
            DiscoveryResults(**project["discovery_results"])
            if project.get("discovery_results")
            else None
        ),
        verification_results=(
            VerificationResults(**project["verification_results"])
            if project.get("verification_results")
            else None
        ),
        comparison_result=(
            ComparisonResult(**project["comparison_result"])
            if project.get("comparison_result")
            else None
        ),
        recommendation=(
            RecommendationResult(**project["recommendation_result"])
            if project.get("recommendation_result")
            else None
        ),
        chat_messages=[ChatMessage(**m) for m in project.get("chat_messages", [])],
        outreach_state=(
            OutreachState(**project["outreach_state"])
            if project.get("outreach_state")
            else None
        ),
        progress_events=project.get("progress_events", []),
        clarifying_questions=project.get("clarifying_questions"),
    )


@router.post("/{project_id}/cancel")
async def cancel_project(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Cancel an in-progress project pipeline."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)

    project_status = project.get("status")
    if project_status in {"complete", "failed", "canceled"}:
        return {
            "project_id": project_id,
            "status": project_status,
            "already_terminal": True,
        }

    if project_status not in ACTIVE_PIPELINE_STATUSES:
        return {
            "project_id": project_id,
            "status": project_status or "idle",
            "already_terminal": True,
        }

    project["status"] = "canceled"
    project["current_stage"] = "canceled"
    project["error"] = project.get("error") or "Canceled by user"
    progress_events = project.setdefault("progress_events", [])
    progress_events.append(
        {
            "stage": "canceled",
            "substep": "user_requested_cancel",
            "detail": "Run canceled by user",
            "progress_pct": None,
            "timestamp": time.time(),
        }
    )
    await record_project_event(
        project,
        event_type="project_canceled",
        title="Run canceled",
        description="You canceled this sourcing run.",
        priority="medium",
        phase="brief",
    )

    await _save_project(project)
    return {"project_id": project_id, "status": "canceled"}


@router.get("/{project_id}/run-sync")
async def run_project_sync(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Run the pipeline synchronously (for testing / demo)."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)
    await _run_pipeline_task(project_id, project["product_description"])
    return await get_project_status(project_id, current_user)


@router.post("/search")
async def quick_search(
    request: ProjectCreateRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Quick synchronous search — runs the full pipeline and returns results."""
    result = await run_pipeline(request.product_description)

    return {
        "status": result.get("current_stage", "unknown"),
        "error": result.get("error"),
        "parsed_requirements": result.get("parsed_requirements"),
        "discovery_results": result.get("discovery_results"),
        "verification_results": result.get("verification_results"),
        "comparison_result": result.get("comparison_result"),
        "recommendation": result.get("recommendation_result"),
    }


@router.get("/{project_id}/logs")
async def get_logs(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Get all stored logs for a project."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)
    return get_project_logs(project_id)


@router.get("/{project_id}/logs/stream")
async def stream_logs(
    project_id: str,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """SSE endpoint — streams live log entries as they happen."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)
    return StreamingResponse(
        subscribe_to_logs(project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.post("/{project_id}/answer")
async def answer_clarifying_questions(
    project_id: str,
    request: ClarifyingAnswerRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Submit answers to clarifying questions and resume the pipeline."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)

    if project.get("status") != "clarifying":
        raise HTTPException(status_code=400, detail="Project is not waiting for answers")

    try:
        project["user_answers"] = request.answers

        reqs = project.get("parsed_requirements", {})
        enhance_prompt = f"""The user was asked clarifying questions about their procurement needs.
Here are their answers:

{request.answers}

Here are the current parsed requirements:

{reqs}

Update the requirements JSON with the user's answers. Fill in missing fields, refine search queries
based on new information, and adjust regional search strategies if needed.
Return ONLY the updated JSON object (same schema as the input requirements)."""

        response = await call_llm_structured(
            prompt=enhance_prompt,
            system="You enhance procurement requirements with user-provided answers. Return only valid JSON.",
            model=settings.model_cheap,
            max_tokens=3000,
        )

        try:
            import json

            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            enhanced = json.loads(text)
            ParsedRequirements(**enhanced)
            project["parsed_requirements"] = enhanced
            logger.info("Enhanced requirements with %d answers", len(request.answers))
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not enhance requirements with answers: %s — continuing with original", e)

        project["clarifying_questions"] = None
        project["status"] = "discovering"
        project["current_stage"] = "discovering"
        await record_project_event(
            project,
            event_type="clarifying_answered",
            title="Clarifications received",
            description=f"Integrated {len(request.answers)} answers and resumed search.",
            priority="info",
            phase="brief",
            payload={"answer_count": len(request.answers)},
        )
        await _save_project(project)

        background_tasks.add_task(_resume_pipeline_task, project_id)

        return {
            "status": "resumed",
            "message": f"Integrated {len(request.answers)} answers, resuming pipeline",
        }

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Answer processing failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{project_id}/clarify")
async def clarify_project_answers_compat(
    project_id: str,
    request: ClarifyingAnswerRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Backward-compatible alias for older frontend clients using /clarify."""
    return await answer_clarifying_questions(
        project_id=project_id,
        request=request,
        background_tasks=background_tasks,
        current_user=current_user,
    )


@router.post("/{project_id}/skip-questions")
async def skip_clarifying_questions(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Skip all clarifying questions and resume the pipeline with existing requirements."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)

    if project.get("status") != "clarifying":
        raise HTTPException(status_code=400, detail="Project is not waiting for answers")

    project["clarifying_questions"] = None
    project["status"] = "discovering"
    project["current_stage"] = "discovering"
    await record_project_event(
        project,
        event_type="clarifying_skipped",
        title="Clarifications skipped",
        description="Skipped clarification questions and resumed search.",
        priority="medium",
        phase="brief",
    )
    await _save_project(project)

    background_tasks.add_task(_resume_pipeline_task, project_id)

    return {"status": "resumed", "message": "Skipped clarifying questions, resuming pipeline"}


@router.get("")
async def list_projects(
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """List all projects (for demo purposes)."""
    store = get_project_store()
    try:
        projects = await store.list_projects()
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc

    return [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "status": p.get("status"),
            "current_stage": p.get("current_stage"),
        }
        for p in projects
        if str(p.get("user_id")) == str(current_user.user_id)
    ]
