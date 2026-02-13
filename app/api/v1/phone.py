"""Phone calling API endpoints — AI-powered supplier phone outreach via Retell."""

import logging
import traceback

from fastapi import APIRouter, HTTPException

from app.agents.phone_agent import (
    get_call_detail,
    initiate_supplier_call,
    parse_call_transcript,
)
from app.schemas.agent_state import (
    DiscoveryResults,
    OutreachState,
    ParsedRequirements,
    PhoneCallConfig,
    PhoneCallStatus,
    SupplierOutreachStatus,
)
from app.schemas.project import PhoneCallConfigRequest, PhoneCallStartRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/phone", tags=["phone"])


def _get_project(project_id: str) -> dict:
    from app.api.v1.projects import _projects

    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_outreach_state(project: dict) -> OutreachState:
    raw = project.get("outreach_state")
    if raw:
        return OutreachState(**raw) if isinstance(raw, dict) else raw
    return OutreachState()


@router.post("/configure")
async def configure_phone(project_id: str, request: PhoneCallConfigRequest):
    """Configure AI phone calling for a project.

    Sets the voice, max duration, and default questions for calls.
    """
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    outreach.phone_config = PhoneCallConfig(
        enabled=request.enabled,
        voice_id=request.voice_id,
        max_call_duration_seconds=request.max_call_duration_seconds,
        questions_to_ask=request.default_questions,
    )

    project["outreach_state"] = outreach.model_dump(mode="json")

    return {
        "status": "configured",
        "config": outreach.phone_config.model_dump(),
    }


@router.post("/call")
async def start_phone_call(project_id: str, request: PhoneCallStartRequest):
    """Initiate an AI phone call to a supplier.

    Creates a Retell AI agent with a customized script and initiates
    an outbound call. The call status can be tracked via webhooks
    or by polling the /calls/{call_id} endpoint.
    """
    project = _get_project(project_id)

    if not project.get("parsed_requirements"):
        raise HTTPException(status_code=400, detail="Pipeline must complete before calling")

    reqs = ParsedRequirements(**project["parsed_requirements"])
    discovery = DiscoveryResults(**project["discovery_results"])

    if request.supplier_index >= len(discovery.suppliers):
        raise HTTPException(status_code=400, detail="Invalid supplier index")

    supplier = discovery.suppliers[request.supplier_index]
    outreach = _get_outreach_state(project)

    # Get phone config defaults
    config = outreach.phone_config or PhoneCallConfig()
    questions = request.questions or config.questions_to_ask

    try:
        call_status = await initiate_supplier_call(
            supplier_name=supplier.name,
            supplier_index=request.supplier_index,
            phone_number=request.phone_number,
            requirements=reqs,
            custom_questions=questions,
            voice_id=config.voice_id,
            max_duration=config.max_call_duration_seconds,
        )

        # Store call in outreach state
        outreach.phone_calls.append(call_status)

        # Update or create supplier outreach status
        found = False
        for status in outreach.supplier_statuses:
            if status.supplier_index == request.supplier_index:
                status.phone_call_id = call_status.call_id
                status.phone_status = "pending"
                found = True
                break

        if not found:
            outreach.supplier_statuses.append(
                SupplierOutreachStatus(
                    supplier_name=supplier.name,
                    supplier_index=request.supplier_index,
                    phone_call_id=call_status.call_id,
                    phone_status="pending",
                )
            )

        project["outreach_state"] = outreach.model_dump(mode="json")

        return {
            "call_id": call_status.call_id,
            "supplier_name": supplier.name,
            "status": call_status.status,
            "phone_number": request.phone_number,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Phone call failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calls")
async def list_phone_calls(project_id: str):
    """List all phone calls for a project."""
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    return {
        "calls": [c.model_dump() for c in outreach.phone_calls],
        "total": len(outreach.phone_calls),
        "config": outreach.phone_config.model_dump() if outreach.phone_config else None,
    }


@router.get("/calls/{call_id}")
async def get_phone_call(project_id: str, call_id: str):
    """Get detailed status of a specific phone call, including transcript."""
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    # Find the call in our state
    local_call = None
    for call in outreach.phone_calls:
        if call.call_id == call_id:
            local_call = call
            break

    if not local_call:
        raise HTTPException(status_code=404, detail="Call not found")

    try:
        # Get latest status from Retell
        detail = await get_call_detail(call_id)

        # Update local state
        local_call.status = detail.get("status", local_call.status)
        local_call.duration_seconds = detail.get("duration_seconds", local_call.duration_seconds)
        local_call.transcript = detail.get("transcript", local_call.transcript)
        local_call.recording_url = detail.get("recording_url", local_call.recording_url)
        local_call.started_at = detail.get("started_at", local_call.started_at)
        local_call.ended_at = detail.get("ended_at", local_call.ended_at)

        project["outreach_state"] = outreach.model_dump(mode="json")

        return local_call.model_dump()

    except Exception as e:
        logger.error("Failed to get call detail: %s", e)
        # Return what we have locally
        return local_call.model_dump()


@router.post("/calls/{call_id}/parse")
async def parse_phone_call(project_id: str, call_id: str):
    """Parse a completed call's transcript into structured procurement data.

    Extracts pricing, MOQ, lead time, and key findings from the transcript.
    """
    project = _get_project(project_id)
    outreach = _get_outreach_state(project)

    # Find the call
    local_call = None
    for call in outreach.phone_calls:
        if call.call_id == call_id:
            local_call = call
            break

    if not local_call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Try to get latest transcript from Retell
    if not local_call.transcript:
        try:
            detail = await get_call_detail(call_id)
            local_call.transcript = detail.get("transcript", "")
            local_call.status = detail.get("status", local_call.status)
        except Exception:
            pass

    if not local_call.transcript:
        raise HTTPException(
            status_code=400,
            detail="No transcript available. Call may still be in progress.",
        )

    try:
        result = await parse_call_transcript(
            transcript=local_call.transcript,
            supplier_name=local_call.supplier_name,
            call_id=call_id,
        )

        # Store parsed result
        outreach.parsed_call_results.append(result)

        # Update supplier status
        for status in outreach.supplier_statuses:
            if status.phone_call_id == call_id:
                status.phone_transcript = local_call.transcript
                break

        project["outreach_state"] = outreach.model_dump(mode="json")

        return result.model_dump()

    except Exception as e:
        logger.error("Call transcript parsing failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
