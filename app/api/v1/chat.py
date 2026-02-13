"""Chat API endpoints — conversational AI advisor for completed projects."""

import json
import logging
import traceback
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.chat_agent import chat_with_context, parse_action_from_response
from app.agents.orchestrator import rerun_from_stage
from app.schemas.agent_state import ChatMessage
from app.schemas.project import ChatMessageRequest
from app.services.project_store import StoreUnavailableError, get_project_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["chat"])


async def _get_project(project_id: str) -> dict:
    """Get project from project store, raise 404 if missing."""
    store = get_project_store()
    try:
        project = await store.get_project(project_id)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _save_project(project: dict) -> None:
    store = get_project_store()
    try:
        await store.save_project(project)
    except StoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Project store unavailable: {exc}") from exc


@router.post("")
async def chat(project_id: str, request: ChatMessageRequest):
    """Send a chat message and get a streaming SSE response."""
    project = await _get_project(project_id)

    if project.get("current_stage") not in ("complete", "failed"):
        raise HTTPException(
            status_code=400,
            detail="Pipeline must be complete before chatting",
        )

    user_msg = ChatMessage(role="user", content=request.message)
    project.setdefault("chat_messages", []).append(user_msg.model_dump(mode="json"))
    await _save_project(project)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in project.get("chat_messages", [])[:-1]
    ]

    async def stream_response():
        full_text = ""
        try:
            async for chunk in chat_with_context(
                user_message=request.message,
                conversation_history=history,
                project_state=project,
            ):
                full_text += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            clean_text, action = parse_action_from_response(full_text)

            assistant_msg = ChatMessage(
                role="assistant",
                content=clean_text,
                metadata={"action": action.model_dump() if action else None},
            )
            project.setdefault("chat_messages", []).append(assistant_msg.model_dump(mode="json"))
            await _save_project(project)

            yield f"data: {json.dumps({'type': 'done', 'action': action.model_dump() if action else None})}\n\n"

            if action and action.action_type != "none":
                result = await _execute_chat_action(project, action.action_type, action.parameters)
                await _save_project(project)
                yield f"data: {json.dumps({'type': 'action_result', 'result': result})}\n\n"

        except Exception as e:  # noqa: BLE001
            logger.error("Chat stream error: %s", traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/history")
async def get_chat_history(project_id: str):
    """Get full chat history for a project."""
    project = await _get_project(project_id)
    return project.get("chat_messages", [])


async def _execute_chat_action(
    project: dict,
    action_type: str,
    parameters: dict[str, Any],
) -> str:
    """Execute a chat-triggered action and update project state."""
    logger.info("Executing chat action: %s with params: %s", action_type, parameters)

    try:
        if action_type in ("rescore", "adjust_weights"):
            weights = parameters.get("weights", {})
            modified = {}
            if weights:
                existing_comparison = project.get("comparison_result", {})
                existing_comparison["_scoring_weights"] = weights
                modified["comparison_result"] = existing_comparison

            state = await rerun_from_stage(project, "compare", modified)
            _sync_rerun_results(project, state)
            return f"Re-scored suppliers with updated weights. {parameters.get('reason', '')}"

        if action_type == "research":
            additional_queries = parameters.get("additional_queries", [])
            modified = {}

            if additional_queries:
                reqs = project.get("parsed_requirements", {})
                existing_queries = reqs.get("search_queries", [])
                reqs["search_queries"] = existing_queries + additional_queries
                modified["parsed_requirements"] = reqs

            state = await rerun_from_stage(project, "discover", modified)
            _sync_rerun_results(project, state)
            new_count = len(state.get("discovery_results", {}).get("suppliers", []))
            return (
                f"Research complete: found {new_count} suppliers after expanding search. "
                f"Re-evaluated and re-ranked all results. {parameters.get('reason', '')}"
            )

        if action_type == "rediscover":
            additional_queries = parameters.get("additional_queries", [])
            modified = {}
            if additional_queries:
                reqs = project.get("parsed_requirements", {})
                existing_queries = reqs.get("search_queries", [])
                reqs["search_queries"] = existing_queries + additional_queries
                modified["parsed_requirements"] = reqs

            state = await rerun_from_stage(project, "discover", modified)
            _sync_rerun_results(project, state)
            return f"Re-ran supplier discovery. {parameters.get('reason', '')}"

        if action_type == "draft_outreach":
            supplier_indices = parameters.get("supplier_indices", [])
            from app.agents.outreach_agent import draft_outreach_emails
            from app.schemas.agent_state import DiscoveryResults, ParsedRequirements, RecommendationResult

            reqs = ParsedRequirements(**project["parsed_requirements"])
            discovery = DiscoveryResults(**project["discovery_results"])
            recs = RecommendationResult(**project["recommendation_result"])

            selected = [
                discovery.suppliers[i]
                for i in supplier_indices
                if i < len(discovery.suppliers)
            ]
            if not selected:
                return "No valid suppliers selected for outreach"

            result = await draft_outreach_emails(selected, reqs, recs)

            outreach = project.get("outreach_state") or {}
            outreach["selected_suppliers"] = supplier_indices
            outreach["draft_emails"] = [d.model_dump(mode="json") for d in result.drafts]
            if "supplier_statuses" not in outreach:
                outreach["supplier_statuses"] = [
                    {
                        "supplier_name": s.name,
                        "supplier_index": i,
                        "email_sent": False,
                        "response_received": False,
                        "follow_ups_sent": 0,
                    }
                    for i, s in zip(supplier_indices, selected)
                ]
            project["outreach_state"] = outreach
            return f"Drafted {len(result.drafts)} RFQ emails. Review them in the Outreach panel."

        return f"Unknown action type: {action_type}"

    except Exception as e:  # noqa: BLE001
        logger.error("Failed to execute chat action %s: %s", action_type, traceback.format_exc())
        return f"Action failed: {str(e)}"


def _sync_rerun_results(project: dict, state: dict) -> None:
    """Push re-run results back into the project dict."""
    if state.get("discovery_results"):
        project["discovery_results"] = state["discovery_results"]
    if state.get("verification_results"):
        project["verification_results"] = state["verification_results"]
    if state.get("comparison_result"):
        project["comparison_result"] = state["comparison_result"]
    if state.get("recommendation_result"):
        project["recommendation_result"] = state["recommendation_result"]
    project["current_stage"] = "complete"
    project["status"] = "complete"
    project["error"] = state.get("error")
