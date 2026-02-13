"""Sourcing project API endpoints.

Supports:
- Pipeline creation and status polling
- Clarifying question pause/resume flow
- Progress event syncing for granular UI updates
"""

import asyncio
import json
import logging
import traceback
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import (
    parse_node,
    discover_node,
    verify_node,
    compare_node,
    recommend_node,
    outreach_node,
    run_pipeline,
    GraphState,
)
from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.core.log_stream import (
    current_project_id,
    get_project_logs,
    subscribe_to_logs,
)
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

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/projects", tags=["projects"])

# In-memory project store for MVP (replace with Supabase in production)
_projects: dict[str, dict[str, Any]] = {}


@router.post("")
async def create_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create a new sourcing project and start the AI pipeline.

    The pipeline runs in the background. Poll GET /projects/{id}/status
    to check progress.
    """
    try:
        project_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())  # TODO: extract from auth

        project = {
            "id": project_id,
            "user_id": user_id,
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

        _projects[project_id] = project

        # Run pipeline in background
        background_tasks.add_task(_run_pipeline_task, project_id, request.product_description)

        return {"project_id": project_id, "status": "started"}

    except Exception as e:
        logger.exception("Failed to create project")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}\n{traceback.format_exc()}")


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
    # Set context var so all log messages and progress events are captured for this project
    current_project_id.set(project_id)

    project = _projects.get(project_id)
    if not project:
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
            # Update project so frontend shows current stage
            project["current_stage"] = stage_name
            project["status"] = stage_name

            state = await step_fn(state)
            # Push results to project dict immediately after each step
            _sync_state_to_project(project, state)

            if state.get("error"):
                logger.error("Pipeline stopped at %s: %s", stage_name, state["error"][:200])
                break

            # After parsing: check for clarifying questions → pause if found
            if stage_name == "parsing":
                reqs = state.get("parsed_requirements") or {}
                questions = reqs.get("clarifying_questions", [])
                if questions:
                    project["status"] = "clarifying"
                    project["current_stage"] = "clarifying"
                    project["clarifying_questions"] = questions
                    logger.info(
                        "Pipeline paused for %d clarifying questions (project %s)",
                        len(questions), project_id,
                    )
                    return  # Pause — user must answer or skip before pipeline continues

        logger.info("Pipeline completed for project %s, stage=%s", project_id, project["current_stage"])

    except Exception as e:
        logger.exception("Pipeline failed for project %s", project_id)
        project["status"] = "failed"
        project["current_stage"] = "failed"
        project["error"] = f"{str(e)}\n{traceback.format_exc()}"


async def _resume_pipeline_task(project_id: str):
    """Resume a paused pipeline from the discover stage onward.

    Called after the user answers clarifying questions or skips them.
    Uses the existing parsed_requirements (possibly enhanced with answers).
    """
    current_project_id.set(project_id)

    project = _projects.get(project_id)
    if not project:
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

    # Only run from discover onwards
    steps = [
        ("discovering", discover_node),
        ("verifying", verify_node),
        ("comparing", compare_node),
        ("recommending", recommend_node),
    ]

    try:
        logger.info("Resuming pipeline for project %s from discover", project_id)

        for stage_name, step_fn in steps:
            project["current_stage"] = stage_name
            project["status"] = stage_name

            state = await step_fn(state)
            _sync_state_to_project(project, state)

            if state.get("error"):
                logger.error("Pipeline stopped at %s: %s", stage_name, state["error"][:200])
                break

        logger.info("Pipeline completed for project %s, stage=%s", project_id, project["current_stage"])

    except Exception as e:
        logger.exception("Pipeline failed for project %s", project_id)
        project["status"] = "failed"
        project["current_stage"] = "failed"
        project["error"] = f"{str(e)}\n{traceback.format_exc()}"


@router.get("/{project_id}/status", response_model=PipelineStatusResponse)
async def get_project_status(project_id: str):
    """Get the current status and results of a sourcing project pipeline."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
        chat_messages=[
            ChatMessage(**m) for m in project.get("chat_messages", [])
        ],
        outreach_state=(
            OutreachState(**project["outreach_state"])
            if project.get("outreach_state")
            else None
        ),
        progress_events=project.get("progress_events", []),
        clarifying_questions=project.get("clarifying_questions"),
    )


@router.get("/{project_id}/run-sync")
async def run_project_sync(project_id: str):
    """
    Run the pipeline synchronously (for testing / demo).
    Blocks until complete. Do not use in production.
    """
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _run_pipeline_task(project_id, project["product_description"])
    return await get_project_status(project_id)


@router.post("/search")
async def quick_search(request: ProjectCreateRequest):
    """
    Quick synchronous search — runs the full pipeline and returns results.
    Use for demos and testing. Production should use async create + poll.
    """
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
async def get_logs(project_id: str):
    """Get all stored logs for a project."""
    return get_project_logs(project_id)


@router.get("/{project_id}/logs/stream")
async def stream_logs(project_id: str):
    """
    SSE endpoint — streams live log entries as they happen.

    Connect from the frontend with EventSource:
        const es = new EventSource('/api/v1/projects/{id}/logs/stream')
        es.onmessage = (e) => console.log(JSON.parse(e.data))
    """
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
):
    """Submit answers to clarifying questions and resume the pipeline.

    The answers are used to enhance the parsed requirements before discovery begins.
    Uses a cheap LLM call to integrate user answers into the existing requirements.
    """
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.get("status") != "clarifying":
        raise HTTPException(status_code=400, detail="Project is not waiting for answers")

    try:
        # Store user answers
        project["user_answers"] = request.answers

        # Enhance parsed requirements with user answers via LLM
        reqs = project.get("parsed_requirements", {})
        enhance_prompt = f"""The user was asked clarifying questions about their procurement needs.
Here are their answers:

{json.dumps(request.answers, indent=2)}

Here are the current parsed requirements:

{json.dumps(reqs, indent=2)}

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
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            enhanced = json.loads(text)
            # Validate it parses as ParsedRequirements
            ParsedRequirements(**enhanced)
            project["parsed_requirements"] = enhanced
            logger.info("Enhanced requirements with %d answers", len(request.answers))
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Could not enhance requirements with answers: %s — continuing with original", e)

        # Clear clarifying state and resume pipeline
        project["clarifying_questions"] = None
        project["status"] = "discovering"
        project["current_stage"] = "discovering"

        background_tasks.add_task(_resume_pipeline_task, project_id)

        return {"status": "resumed", "message": f"Integrated {len(request.answers)} answers, resuming pipeline"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Answer processing failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/skip-questions")
async def skip_clarifying_questions(
    project_id: str,
    background_tasks: BackgroundTasks,
):
    """Skip all clarifying questions and resume the pipeline with existing requirements."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.get("status") != "clarifying":
        raise HTTPException(status_code=400, detail="Project is not waiting for answers")

    # Clear clarifying state and resume
    project["clarifying_questions"] = None
    project["status"] = "discovering"
    project["current_stage"] = "discovering"

    background_tasks.add_task(_resume_pipeline_task, project_id)

    return {"status": "resumed", "message": "Skipped clarifying questions, resuming pipeline"}


@router.get("")
async def list_projects():
    """List all projects (for demo purposes)."""
    return [
        {
            "id": p["id"],
            "title": p["title"],
            "status": p["status"],
            "current_stage": p["current_stage"],
        }
        for p in _projects.values()
    ]
