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
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import (
    checkpoint_node,
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
from app.core.progress import emit_progress
from app.schemas.agent_state import (
    ChatMessage,
    CheckpointResponse,
    CheckpointType,
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
    ProjectDecisionPreferenceRequest,
    ProjectCreateRequest,
    ProjectRestartRequest,
)
from app.schemas.buyer_context import BuyerContext
from app.schemas.retrospective import RetrospectiveRequest
from app.services.buyer_context_builder import (
    merge_checkpoint_answers,
    update_user_profile_from_project,
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
    "steering",
    "comparing",
    "recommending",
    "outreaching",
}
LISTABLE_PROJECT_STATUSES = ACTIVE_PIPELINE_STATUSES | {"complete", "failed", "canceled"}
TERMINAL_PROJECT_STATUSES = {"complete", "failed", "canceled"}
PROJECT_START_FAILURE_DETAIL = "Failed to start project. Please try again."
PROJECT_ANSWER_FAILURE_DETAIL = "Failed to process answers. Please try again."
PROJECT_RETROSPECTIVE_ALREADY_SUBMITTED_DETAIL = "Retrospective has already been submitted for this project."

RESTARTABLE_STAGES = {"parsing", "discovering"}
DECISION_LANES = {"best_overall", "best_low_risk", "best_speed_to_order"}

_STAGE_PHASE = {
    "parsing": "brief",
    "clarifying": "brief",
    "steering": "brief",
    "discovering": "search",
    "verifying": "search",
    "comparing": "compare",
    "recommending": "compare",
    "outreaching": "outreach",
    "complete": "order",
    "failed": "brief",
    "canceled": "brief",
}


def normalize_project_status_filters(status_values: list[str] | None) -> set[str] | None:
    """Normalize list query filters and expand supported aliases."""
    if not status_values:
        return None

    normalized: set[str] = set()
    for raw_value in status_values:
        if not raw_value:
            continue
        for token in raw_value.split(","):
            cleaned = token.strip().lower()
            if cleaned:
                normalized.add(cleaned)
    if not normalized:
        return None

    expanded: set[str] = set()
    for value in normalized:
        if value == "active":
            expanded.update(ACTIVE_PIPELINE_STATUSES)
            continue
        if value == "closed":
            expanded.update(TERMINAL_PROJECT_STATUSES)
            continue
        expanded.add(value)

    invalid_statuses = sorted(expanded - LISTABLE_PROJECT_STATUSES)
    if invalid_statuses:
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid status filter value(s): "
                + ", ".join(invalid_statuses)
                + ". Allowed values: "
                + ", ".join(sorted(LISTABLE_PROJECT_STATUSES | {"active", "closed"}))
            ),
        )

    return expanded


def _normalized_project_status(project: dict) -> str:
    return str(project.get("status") or "").strip().lower()


def _normalized_stage_name(project: dict) -> str:
    """Return a canonical stage name for list responses."""
    normalized_stage = str(project.get("current_stage") or "").strip().lower()
    if normalized_stage:
        return normalized_stage
    return _normalized_project_status(project)


def _normalized_status_name(project: dict) -> str:
    """Return canonical status, falling back to canonical stage when status is absent."""
    normalized_status = _normalized_project_status(project)
    if normalized_status:
        return normalized_status
    return _normalized_stage_name(project)


def _stage_title(stage_name: str) -> str:
    titles = {
        "parsing": "Parsing requirements",
        "steering": "Review checkpoint",
        "discovering": "Searching suppliers",
        "verifying": "Verifying suppliers",
        "comparing": "Comparing options",
        "recommending": "Generating recommendation",
        "outreaching": "Running outreach",
    }
    return titles.get(stage_name, stage_name.replace("_", " ").title())


def _stage_progress_message(stage_name: str) -> str:
    messages = {
        "parsing": "Reading your brief and setting up the sourcing plan.",
        "steering": "Waiting for your steering input, or continuing with defaults shortly.",
        "discovering": "Searching for suppliers that match your requirements.",
        "verifying": "Checking supplier legitimacy, contact data, and fit.",
        "comparing": "Comparing top suppliers across cost, quality, and speed.",
        "recommending": "Preparing a clear shortlist with next best actions.",
        "outreaching": "Drafting and sending supplier outreach on your behalf.",
    }
    return messages.get(stage_name, f"Working on {stage_name.replace('_', ' ')}.")


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
    project.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    project["updated_at"] = datetime.now(timezone.utc).isoformat()
    store = get_project_store()
    try:
        await store.save_project(project)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


async def _create_project(project: dict) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    project.setdefault("created_at", now_iso)
    project.setdefault("updated_at", now_iso)
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
            "decision_preference": None,
            "buyer_context": None,
            "user_sourcing_profile": None,
            "active_checkpoint": None,
            "checkpoint_responses": {},
            "confidence_gate_threshold": 30.0,
            "retrospective": None,
            "proactive_alerts": [],
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
        raise HTTPException(status_code=500, detail=PROJECT_START_FAILURE_DETAIL) from e


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
    if "buyer_context" in state:
        project["buyer_context"] = state.get("buyer_context")
    if "user_sourcing_profile" in state:
        project["user_sourcing_profile"] = state.get("user_sourcing_profile")
    if "gated_suppliers" in state:
        project["gated_suppliers"] = state.get("gated_suppliers", [])
    if "confidence_gate_threshold" in state:
        project["confidence_gate_threshold"] = state.get("confidence_gate_threshold")
    if "active_checkpoint" in state:
        project["active_checkpoint"] = state.get("active_checkpoint")
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
        "user_id": project.get("user_id"),
        "buyer_context": project.get("buyer_context"),
        "user_sourcing_profile": project.get("user_sourcing_profile"),
        "active_checkpoint": project.get("active_checkpoint"),
        "checkpoint_responses": project.get("checkpoint_responses", {}) or {},
        "confidence_gate_threshold": float(project.get("confidence_gate_threshold") or 30.0),
        "checkpoint_auto_continue": not settings.enable_checkpoints,
    }

    steps = [
        ("parsing", parse_node),
        ("discovering", discover_node),
        ("verifying", verify_node),
        ("comparing", compare_node),
        ("recommending", recommend_node),
    ]
    checkpoint_by_stage = {
        "parsing": CheckpointType.CONFIRM_REQUIREMENTS,
        "discovering": CheckpointType.REVIEW_SUPPLIERS,
        "verifying": CheckpointType.SET_CONFIDENCE_GATE,
        "comparing": CheckpointType.ADJUST_WEIGHTS,
        "recommending": CheckpointType.OUTREACH_PREFERENCES,
    }

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
            emit_progress(stage_name, "stage_started", _stage_progress_message(stage_name))
            await record_project_event(
                project,
                event_type="stage_started",
                title=_stage_title(stage_name),
                description=f"Procurement AI started {stage_name.replace('_', ' ')}.",
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

            if state.get("error"):
                logger.error("Pipeline stopped at %s: %s", stage_name, state["error"][:200])
                emit_progress("failed", "pipeline_failed", "The run failed. You can retry with updated context.")
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
                return

            await record_project_event(
                project,
                event_type="stage_completed",
                title=f"{_stage_title(stage_name)} complete",
                description=f"Procurement AI completed {stage_name.replace('_', ' ')}.",
                priority="info",
                phase=_STAGE_PHASE.get(stage_name),
                payload={"stage": stage_name},
            )
            emit_progress(stage_name, "stage_complete", f"{_stage_title(stage_name)} complete.")
            await store.save_project(project)

            if settings.enable_checkpoints:
                checkpoint_type = checkpoint_by_stage.get(stage_name)
                if checkpoint_type:
                    state = await checkpoint_node(state, checkpoint_type)
                    _sync_state_to_project(project, state)
                    project["status"] = state.get("current_stage", project.get("status"))
                    project["current_stage"] = state.get("current_stage", project.get("current_stage"))
                    await store.save_project(project)

                    if state.get("current_stage") == PipelineStage.STEERING.value:
                        emit_progress(
                            "steering",
                            checkpoint_type.value,
                            "Checkpoint ready. Continue now or provide steering input.",
                        )
                        await record_project_event(
                            project,
                            event_type="checkpoint_ready",
                            title="Checkpoint ready",
                            description=(state.get("active_checkpoint") or {}).get(
                                "summary",
                                "Review this stage before continuing.",
                            ),
                            priority="medium",
                            phase=_STAGE_PHASE.get(stage_name),
                            payload={
                                "checkpoint_type": checkpoint_type.value,
                                "auto_continue_seconds": (state.get("active_checkpoint") or {}).get(
                                    "auto_continue_seconds"
                                ),
                            },
                        )
                        await store.save_project(project)
                        logger.info("Pipeline paused at checkpoint %s (project %s)", checkpoint_type.value, project_id)
                        return

            if stage_name == "recommending" and settings.feature_focus_circle_search_v1:
                recommendation = project.get("recommendation_result") or {}
                lane_coverage = recommendation.get("lane_coverage") or {}
                if isinstance(lane_coverage, dict):
                    primary_coverage = {lane: int(lane_coverage.get(lane, 0) or 0) for lane in DECISION_LANES}
                    missing_lanes = [lane for lane, count in primary_coverage.items() if count < 1]
                    if missing_lanes:
                        await record_project_event(
                            project,
                            event_type="recommendation_lane_coverage_low",
                            title="Recommendation lane coverage is thin",
                            description=(
                                "Recommendation output did not fully cover decision lanes: "
                                + ", ".join(missing_lanes)
                            ),
                            priority="medium",
                            phase="compare",
                            payload={
                                "lane_coverage": primary_coverage,
                                "missing_lanes": missing_lanes,
                            },
                        )

            if stage_name == "parsing" and not settings.enable_checkpoints:
                reqs = state.get("parsed_requirements") or {}
                questions = reqs.get("clarifying_questions", [])
                if questions:
                    enhanced_questions = 0
                    if settings.feature_focus_circle_search_v1:
                        for question in questions:
                            if not isinstance(question, dict):
                                continue
                            if (
                                question.get("why_this_question")
                                or question.get("if_skipped_impact")
                                or question.get("suggested_default")
                            ):
                                enhanced_questions += 1
                        if enhanced_questions:
                            await record_project_event(
                                project,
                                event_type="clarification_question_enhanced",
                                title="Clarification guidance added",
                                description=(
                                    f"Added rationale/default guidance to {enhanced_questions} "
                                    "clarification question(s)."
                                ),
                                priority="info",
                                phase="brief",
                                payload={"enhanced_count": enhanced_questions},
                            )
                    project["status"] = "clarifying"
                    project["current_stage"] = "clarifying"
                    project["clarifying_questions"] = questions
                    emit_progress(
                        "clarifying",
                        "awaiting_answers",
                        "Need a few details from you before continuing the supplier search.",
                    )
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

        if state.get("error") or project.get("current_stage") in {"failed", "canceled"}:
            logger.info(
                "Skipping completion marker for project %s due terminal state: %s",
                project_id,
                project.get("current_stage"),
            )
            return

        project["status"] = "complete"
        project["current_stage"] = "complete"
        project["error"] = None

        await record_project_event(
            project,
            event_type="project_completed",
            title="Pipeline complete",
            description="Discovery, verification, and recommendation are ready.",
            priority="info",
            phase=_STAGE_PHASE.get(project.get("current_stage")),
        )
        emit_progress("complete", "ready", "Your shortlist is ready. Review suppliers and approve outreach.")
        if settings.enable_buyer_context and project.get("buyer_context") and project.get("user_id"):
            try:
                context = BuyerContext(**(project.get("buyer_context") or {}))
                await update_user_profile_from_project(
                    user_id=str(project.get("user_id")),
                    project_state=project,
                    buyer_context=context,
                )
            except Exception:
                logger.warning("Profile update after project completion failed", exc_info=True)
        await store.save_project(project)
        logger.info("Pipeline completed for project %s, stage=%s", project_id, project["current_stage"])

    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline failed for project %s", project_id)
        project["status"] = "failed"
        project["current_stage"] = "failed"
        project["error"] = f"{str(e)}\n{traceback.format_exc()}"
        emit_progress("failed", "pipeline_crash", "The run stopped unexpectedly. Try restarting from the brief.")
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


async def _resume_pipeline_task(project_id: str, from_stage: str | None = None):
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

    stage_name = (from_stage or project.get("current_stage") or "discovering").strip().lower()
    if stage_name == "steering":
        stage_name = "discovering"

    state: GraphState = {
        "raw_description": project.get("product_description", ""),
        "current_stage": stage_name,
        "error": None,
        "parsed_requirements": project.get("parsed_requirements"),
        "discovery_results": project.get("discovery_results"),
        "verification_results": project.get("verification_results"),
        "comparison_result": project.get("comparison_result"),
        "recommendation_result": project.get("recommendation_result"),
        "outreach_result": project.get("outreach_state"),
        "progress_events": project.get("progress_events", []),
        "user_answers": project.get("user_answers"),
        "auto_outreach_enabled": bool(project.get("auto_outreach")),
        "user_id": project.get("user_id"),
        "buyer_context": project.get("buyer_context"),
        "user_sourcing_profile": project.get("user_sourcing_profile"),
        "active_checkpoint": project.get("active_checkpoint"),
        "checkpoint_responses": project.get("checkpoint_responses", {}) or {},
        "confidence_gate_threshold": float(project.get("confidence_gate_threshold") or 30.0),
        "checkpoint_auto_continue": not settings.enable_checkpoints,
    }

    full_steps = [
        ("discovering", discover_node),
        ("verifying", verify_node),
        ("comparing", compare_node),
        ("recommending", recommend_node),
    ]
    if project.get("auto_outreach"):
        full_steps.append(("outreaching", outreach_node))

    stage_order = [name for name, _ in full_steps]
    if stage_name not in stage_order:
        stage_name = "discovering"
    start_index = stage_order.index(stage_name)
    steps = full_steps[start_index:]
    checkpoint_by_stage = {
        "discovering": CheckpointType.REVIEW_SUPPLIERS,
        "verifying": CheckpointType.SET_CONFIDENCE_GATE,
        "comparing": CheckpointType.ADJUST_WEIGHTS,
        "recommending": CheckpointType.OUTREACH_PREFERENCES,
    }

    try:
        logger.info("Resuming pipeline for project %s from %s", project_id, stage_name)

        for stage_name, step_fn in steps:
            should_stop, latest_project = await _should_stop_for_cancellation(store, project_id)
            if should_stop:
                return
            project = latest_project or project

            project["current_stage"] = stage_name
            project["status"] = stage_name
            emit_progress(stage_name, "stage_started", _stage_progress_message(stage_name))
            await record_project_event(
                project,
                event_type="stage_started",
                title=_stage_title(stage_name),
                description=f"Procurement AI resumed and started {stage_name.replace('_', ' ')}.",
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

            if state.get("error"):
                logger.error("Pipeline stopped at %s: %s", stage_name, state["error"][:200])
                emit_progress("failed", "pipeline_failed", "The run failed. You can retry with updated context.")
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
                return

            await record_project_event(
                project,
                event_type="stage_completed",
                title=f"{_stage_title(stage_name)} complete",
                description=f"Procurement AI completed {stage_name.replace('_', ' ')}.",
                priority="info",
                phase=_STAGE_PHASE.get(stage_name),
                payload={"stage": stage_name, "resume": True},
            )
            emit_progress(stage_name, "stage_complete", f"{_stage_title(stage_name)} complete.")
            await store.save_project(project)

            if settings.enable_checkpoints:
                checkpoint_type = checkpoint_by_stage.get(stage_name)
                if checkpoint_type:
                    state = await checkpoint_node(state, checkpoint_type)
                    _sync_state_to_project(project, state)
                    project["status"] = state.get("current_stage", project.get("status"))
                    project["current_stage"] = state.get("current_stage", project.get("current_stage"))
                    await store.save_project(project)

                    if state.get("current_stage") == PipelineStage.STEERING.value:
                        emit_progress(
                            "steering",
                            checkpoint_type.value,
                            "Checkpoint ready. Continue now or provide steering input.",
                        )
                        await record_project_event(
                            project,
                            event_type="checkpoint_ready",
                            title="Checkpoint ready",
                            description=(state.get("active_checkpoint") or {}).get(
                                "summary",
                                "Review this stage before continuing.",
                            ),
                            priority="medium",
                            phase=_STAGE_PHASE.get(stage_name),
                            payload={
                                "checkpoint_type": checkpoint_type.value,
                                "resume": True,
                            },
                        )
                        await store.save_project(project)
                        logger.info("Pipeline paused at checkpoint %s (project %s)", checkpoint_type.value, project_id)
                        return

            if stage_name == "recommending" and settings.feature_focus_circle_search_v1:
                recommendation = project.get("recommendation_result") or {}
                lane_coverage = recommendation.get("lane_coverage") or {}
                if isinstance(lane_coverage, dict):
                    primary_coverage = {lane: int(lane_coverage.get(lane, 0) or 0) for lane in DECISION_LANES}
                    missing_lanes = [lane for lane, count in primary_coverage.items() if count < 1]
                    if missing_lanes:
                        await record_project_event(
                            project,
                            event_type="recommendation_lane_coverage_low",
                            title="Recommendation lane coverage is thin",
                            description=(
                                "Recommendation output did not fully cover decision lanes: "
                                + ", ".join(missing_lanes)
                            ),
                            priority="medium",
                            phase="compare",
                            payload={
                                "lane_coverage": primary_coverage,
                                "missing_lanes": missing_lanes,
                            },
                        )

        if state.get("error") or project.get("current_stage") in {"failed", "canceled"}:
            logger.info(
                "Skipping completion marker for resumed project %s due terminal state: %s",
                project_id,
                project.get("current_stage"),
            )
            return

        project["status"] = "complete"
        project["current_stage"] = "complete"
        project["error"] = None

        await record_project_event(
            project,
            event_type="project_completed",
            title="Pipeline complete",
            description="Discovery, verification, and recommendation are ready.",
            priority="info",
            phase=_STAGE_PHASE.get(project.get("current_stage")),
        )
        emit_progress("complete", "ready", "Your shortlist is ready. Review suppliers and approve outreach.")
        if settings.enable_buyer_context and project.get("buyer_context") and project.get("user_id"):
            try:
                context = BuyerContext(**(project.get("buyer_context") or {}))
                await update_user_profile_from_project(
                    user_id=str(project.get("user_id")),
                    project_state=project,
                    buyer_context=context,
                )
            except Exception:
                logger.warning("Profile update after resumed completion failed", exc_info=True)
        await store.save_project(project)
        logger.info("Pipeline completed for project %s, stage=%s", project_id, project["current_stage"])

    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline failed for project %s", project_id)
        project["status"] = "failed"
        project["current_stage"] = "failed"
        project["error"] = f"{str(e)}\n{traceback.format_exc()}"
        emit_progress("failed", "pipeline_crash", "The run stopped unexpectedly. Try restarting from the brief.")
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
        status=_normalized_status_name(project),
        current_stage=_normalized_stage_name(project),
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
        decision_preference=project.get("decision_preference"),
        buyer_context=project.get("buyer_context"),
        retrospective=project.get("retrospective"),
        active_checkpoint=project.get("active_checkpoint"),
        proactive_alerts=project.get("proactive_alerts", []),
    )


@router.post("/{project_id}/decision-preference")
async def set_project_decision_preference(
    project_id: str,
    request: ProjectDecisionPreferenceRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)

    lane_preference = request.lane_preference
    project["decision_preference"] = lane_preference

    await record_project_event(
        project,
        event_type="decision_preference_set",
        title="Decision lane selected",
        description=f"Lane preference set to {lane_preference.replace('_', ' ')}.",
        priority="info",
        phase="compare",
        payload={"lane_preference": lane_preference},
    )
    await _save_project(project)

    return {"project_id": project_id, "lane_preference": lane_preference}


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


@router.post("/{project_id}/restart")
async def restart_project(
    project_id: str,
    request: ProjectRestartRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Restart the pipeline from parsing or discovery, optionally with added context."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)

    project_status = str(project.get("status") or "")
    if project_status in ACTIVE_PIPELINE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Project is currently running. Cancel the run before restarting.",
        )

    requested_stage = (request.from_stage or "discovering").strip().lower()
    if requested_stage not in RESTARTABLE_STAGES:
        raise HTTPException(status_code=400, detail="from_stage must be 'parsing' or 'discovering'")

    additional_context = (request.additional_context or "").strip()
    restart_stage = requested_stage
    if additional_context and restart_stage != "parsing":
        # Any new context should re-run parsing to avoid stale requirement assumptions.
        restart_stage = "parsing"

    if restart_stage == "discovering" and not project.get("parsed_requirements"):
        restart_stage = "parsing"

    if additional_context:
        base_description = (project.get("product_description") or "").strip()
        project["product_description"] = (
            f"{base_description}\n\nAdditional context:\n{additional_context}"
            if base_description
            else additional_context
        )

    project["status"] = restart_stage
    project["current_stage"] = restart_stage
    project["error"] = None
    project["discovery_results"] = None
    project["verification_results"] = None
    project["comparison_result"] = None
    project["recommendation_result"] = None
    project["outreach_state"] = None
    project["decision_preference"] = None
    project["active_checkpoint"] = None
    project["checkpoint_responses"] = {}
    project["gated_suppliers"] = []

    if restart_stage == "parsing":
        project["parsed_requirements"] = None
        project["clarifying_questions"] = None
        project["user_answers"] = None
    else:
        project["clarifying_questions"] = None

    project.setdefault("progress_events", []).append(
        {
            "stage": restart_stage,
            "substep": "restart_requested",
            "detail": (
                "Restarting from brief with your new context."
                if additional_context
                else "Restarting supplier search with your current brief."
            ),
            "progress_pct": None,
            "timestamp": time.time(),
        }
    )

    await record_project_event(
        project,
        event_type="project_restarted",
        title="Pipeline restarted",
        description=(
            "Restarted from brief with extra context."
            if additional_context
            else "Restarted supplier search from current brief."
        ),
        priority="medium",
        phase="brief" if restart_stage == "parsing" else "search",
        payload={
            "from_stage": restart_stage,
            "has_additional_context": bool(additional_context),
        },
    )
    await _save_project(project)

    emit_progress(
        restart_stage,
        "restart_requested",
        "Got it. Restarting the sourcing flow now.",
    )
    if restart_stage == "parsing":
        background_tasks.add_task(_run_pipeline_task, project_id, project.get("product_description", ""))
    else:
        background_tasks.add_task(_resume_pipeline_task, project_id)

    return {
        "project_id": project_id,
        "status": "restarted",
        "from_stage": restart_stage,
        "message": (
            "Restarted from brief with added context."
            if additional_context
            else "Restarted supplier search."
        ),
    }


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
        raise HTTPException(status_code=500, detail=PROJECT_ANSWER_FAILURE_DETAIL) from e


@router.post("/{project_id}/checkpoint")
async def respond_to_checkpoint(
    project_id: str,
    response: CheckpointResponse,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Submit user's response to an active steering checkpoint and resume pipeline."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)

    active_checkpoint = project.get("active_checkpoint") or {}
    if project.get("status") != PipelineStage.STEERING.value or not active_checkpoint:
        raise HTTPException(status_code=400, detail="Project is not awaiting checkpoint input")

    active_type = active_checkpoint.get("checkpoint_type")
    if active_type != response.checkpoint_type.value:
        raise HTTPException(
            status_code=400,
            detail=f"Checkpoint mismatch. Active checkpoint: {active_type}",
        )

    project.setdefault("checkpoint_responses", {})[response.checkpoint_type.value] = response.model_dump(mode="json")

    # Merge answers into buyer context for immediate persistence.
    context = BuyerContext(**(project.get("buyer_context") or {}))
    context = await merge_checkpoint_answers(context, response.answers)
    project["buyer_context"] = context.model_dump(mode="json")
    project["active_checkpoint"] = None

    # Route to the next stage before background resume starts.
    stage_after = {
        CheckpointType.CONFIRM_REQUIREMENTS: "discovering",
        CheckpointType.REVIEW_SUPPLIERS: "verifying",
        CheckpointType.SET_CONFIDENCE_GATE: "comparing",
        CheckpointType.ADJUST_WEIGHTS: "recommending",
        CheckpointType.OUTREACH_PREFERENCES: "outreaching" if project.get("auto_outreach") else "complete",
    }
    next_stage = stage_after[response.checkpoint_type]
    project["status"] = next_stage
    project["current_stage"] = next_stage

    await record_project_event(
        project,
        event_type="checkpoint_answered",
        title="Checkpoint updated",
        description=f"Applied steering for {response.checkpoint_type.value}.",
        priority="info",
        phase=_STAGE_PHASE.get(next_stage),
        payload={
            "checkpoint_type": response.checkpoint_type.value,
            "action": response.action,
        },
    )
    await _save_project(project)

    if next_stage in {"discovering", "verifying", "comparing", "recommending", "outreaching"}:
        background_tasks.add_task(_resume_pipeline_task, project_id, next_stage)

    return {
        "project_id": project_id,
        "status": "resumed",
        "next_stage": next_stage,
    }


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


@router.post("/{project_id}/retrospective")
async def submit_retro(
    project_id: str,
    request: RetrospectiveRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Persist post-project retrospective feedback and update user profile learning."""
    project = await _get_project_or_404(project_id)
    _enforce_project_ownership(project, current_user)
    if _normalized_status_name(project) != "complete":
        raise HTTPException(
            status_code=400,
            detail="Retrospective can only be submitted for completed projects",
        )
    if project.get("retrospective"):
        raise HTTPException(
            status_code=409,
            detail=PROJECT_RETROSPECTIVE_ALREADY_SUBMITTED_DETAIL,
        )

    project["retrospective"] = request.model_dump(mode="json")

    try:
        context = BuyerContext(**(project.get("buyer_context") or {}))
        await update_user_profile_from_project(
            user_id=str(current_user.user_id),
            project_state=project,
            buyer_context=context,
            user_feedback=request.model_dump(mode="json"),
        )
    except Exception:
        logger.warning("Failed to update user profile from retrospective", exc_info=True)

    await record_project_event(
        project,
        event_type="retrospective_submitted",
        title="Retrospective recorded",
        description="Captured post-project feedback for future sourcing improvements.",
        priority="info",
        phase="order",
    )
    await _save_project(project)

    return {"project_id": project_id, "status": "recorded"}


@router.get("")
async def list_projects(
    current_user: AuthUser = Depends(get_current_auth_user),
    status: list[str] | None = Query(
        default=None,
        description=(
            "Optional project status filter. Repeat the parameter to include multiple values, "
            "for example ?status=parsing&status=discovering."
        ),
    ),
    q: str | None = Query(
        default=None,
        max_length=120,
        description="Optional case-insensitive project title or description keyword filter.",
    ),
):
    """List current user's projects with active work first, then recent activity."""
    store = get_project_store()
    try:
        projects = await store.list_projects()
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc

    def _timestamp_sort_value(project: dict, field: str) -> float:
        value = project.get(field)
        if isinstance(value, (int, float)):
            return float(value)
        if not value:
            return 0.0
        try:
            normalized = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).timestamp()
        except ValueError:
            return 0.0

    def _sort_key(project: dict) -> tuple[int, float, float]:
        status = _normalized_status_name(project)
        is_active = 1 if status in ACTIVE_PIPELINE_STATUSES else 0
        updated = _timestamp_sort_value(project, "updated_at")
        created = _timestamp_sort_value(project, "created_at")
        return (is_active, updated, created)

    normalized_statuses = normalize_project_status_filters(status)
    query_text = (q or "").strip().lower()

    user_projects = [p for p in projects if str(p.get("user_id")) == str(current_user.user_id)]
    if normalized_statuses:
        user_projects = [project for project in user_projects if _normalized_status_name(project) in normalized_statuses]
    if query_text:
        user_projects = [
            project
            for project in user_projects
            if query_text in str(project.get("title") or "").strip().lower()
            or query_text in str(project.get("product_description") or "").strip().lower()
        ]
    ordered_projects = sorted(user_projects, key=_sort_key, reverse=True)

    return [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "status": _normalized_status_name(p),
            "current_stage": _normalized_stage_name(p),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
        }
        for p in ordered_projects
    ]
