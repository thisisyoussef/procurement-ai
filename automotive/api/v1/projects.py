"""API endpoints for automotive procurement projects."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from automotive.services.project_service import (
    _in_memory_projects,
    approve_stage,
    create_project,
    get_project,
    list_projects,
)

router = APIRouter(prefix="/projects", tags=["automotive-projects"])


class CreateProjectRequest(BaseModel):
    raw_request: str = Field(description="Natural language procurement description")
    buyer_company: str = ""
    buyer_contact_name: str = ""
    buyer_contact_email: str = ""


class ApproveStageRequest(BaseModel):
    stage: str
    approved: bool = True
    edits: Optional[dict] = None
    removed_supplier_ids: Optional[list[str]] = None
    status_overrides: Optional[dict[str, str]] = None
    weight_adjustments: Optional[dict[str, float]] = None
    corrections: Optional[list[dict]] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


@router.post("")
async def create_automotive_project(
    body: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new automotive procurement project and start the pipeline."""
    result = await create_project(
        db=db,
        raw_request=body.raw_request,
        buyer_company=body.buyer_company,
        buyer_contact_name=body.buyer_contact_name,
        buyer_contact_email=body.buyer_contact_email,
    )
    return result


@router.get("")
async def list_automotive_projects(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all automotive procurement projects."""
    return await list_projects(db=db)


@router.get("/{project_id}")
async def get_automotive_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific automotive procurement project with full state."""
    project = await get_project(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/stage/{stage}")
async def get_project_stage_data(
    project_id: str,
    stage: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get data for a specific pipeline stage."""
    project = await get_project(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stage_map = {
        "parse": "parsed_requirement",
        "discover": "discovery_result",
        "qualify": "qualification_result",
        "compare": "comparison_matrix",
        "report": "intelligence_reports",
        "rfq": "rfq_result",
        "quote_ingest": "quote_ingestion",
    }

    key = stage_map.get(stage)
    if not key:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {stage}")

    return {
        "stage": stage,
        "current_stage": project.get("current_stage"),
        "data": project.get(key),
    }


@router.post("/{project_id}/approve")
async def approve_project_stage(
    project_id: str,
    body: ApproveStageRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Submit human approval for a pipeline gate."""
    decision = body.model_dump(exclude_none=True)
    result = await approve_stage(
        db=db,
        project_id=project_id,
        stage=body.stage,
        decision=decision,
    )
    return result


@router.get("/{project_id}/suppliers")
async def get_project_suppliers(
    project_id: str,
    stage: str = "qualify",
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get suppliers for a project at the specified stage."""
    project = await get_project(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if stage == "discover":
        result = project.get("discovery_result", {})
        return result.get("suppliers", [])
    elif stage == "qualify":
        result = project.get("qualification_result", {})
        return result.get("suppliers", [])
    elif stage == "compare":
        result = project.get("comparison_matrix", {})
        return result.get("suppliers", [])
    else:
        return []


@router.get("/{project_id}/comparison")
async def get_project_comparison(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the comparison matrix for a project."""
    project = await get_project(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.get("comparison_matrix") or {}


@router.get("/{project_id}/reports/{supplier_id}")
async def get_supplier_report(
    project_id: str,
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the intelligence report for a specific supplier."""
    project = await get_project(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    reports = project.get("intelligence_reports", {})
    for report in reports.get("reports", []):
        if report.get("supplier_id") == supplier_id:
            return report

    raise HTTPException(status_code=404, detail="Report not found for this supplier")


@router.get("/{project_id}/rfq")
async def get_project_rfq(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the RFQ package for review."""
    project = await get_project(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.get("rfq_result") or {}


@router.get("/{project_id}/quotes")
async def get_project_quotes(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get parsed quotes for a project."""
    project = await get_project(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.get("quote_ingestion") or {}


@router.get("/{project_id}/debug")
async def debug_project_state(project_id: str) -> dict[str, Any]:
    """DEBUG: Return raw in-memory project state for troubleshooting."""
    proj = _in_memory_projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found in memory")
    # Return keys and types (truncate large values to avoid flooding)
    summary: dict[str, Any] = {}
    for k, v in proj.items():
        if v is None:
            summary[k] = None
        elif isinstance(v, dict):
            summary[k] = {"_type": "dict", "_keys": list(v.keys()), "_len": len(v)}
        elif isinstance(v, list):
            summary[k] = {"_type": "list", "_len": len(v)}
        elif isinstance(v, str) and len(v) > 200:
            summary[k] = v[:200] + "..."
        else:
            summary[k] = v
    return summary
