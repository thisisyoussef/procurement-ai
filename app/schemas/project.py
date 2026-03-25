"""Sourcing project API request/response schemas."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.agent_state import (
    ChatMessage,
    CheckpointEvent,
    ComparisonResult,
    DiscoveryResults,
    OutreachState,
    ParsedRequirements,
    RecommendationResult,
    VerificationResults,
)


class ProjectCreateRequest(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    product_description: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=10, max_length=5000),
    ]
    auto_outreach: bool = Field(
        default=False,
        description="If True, automatically draft and send outreach emails after recommendations",
    )


class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    product_description: str
    status: str
    parsed_requirements: ParsedRequirements | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Full project response including all agent results."""
    discovery_results: DiscoveryResults | None = None
    verification_results: VerificationResults | None = None
    comparison_result: ComparisonResult | None = None
    recommendation: RecommendationResult | None = None


class PipelineStatusResponse(BaseModel):
    project_id: UUID
    status: str
    current_stage: str
    error: str | None = None
    parsed_requirements: ParsedRequirements | None = None
    discovery_results: DiscoveryResults | None = None
    verification_results: VerificationResults | None = None
    comparison_result: ComparisonResult | None = None
    recommendation: RecommendationResult | None = None
    chat_messages: list[ChatMessage] = Field(default_factory=list)
    outreach_state: OutreachState | None = None
    progress_events: list[dict] = Field(default_factory=list)
    clarifying_questions: list[dict] | None = None
    decision_preference: str | None = None
    buyer_context: dict[str, Any] | None = None
    retrospective: dict[str, Any] | None = None
    active_checkpoint: CheckpointEvent | None = None
    proactive_alerts: list[dict] = Field(default_factory=list)


# ── Chat request/response ──────────────────────────────────────

class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


# ── Outreach requests ─────────────────────────────────────────

class OutreachStartRequest(BaseModel):
    supplier_indices: list[int] = Field(min_length=1)


class EmailApprovalRequest(BaseModel):
    draft_index: int
    edited_subject: str | None = None
    edited_body: str | None = None


class QuoteParseRequest(BaseModel):
    supplier_index: int
    response_text: str = Field(min_length=10, max_length=20000)


class OutreachQuickApprovalRequest(BaseModel):
    approve: bool = True
    max_suppliers: int = Field(default=3, ge=1, le=10)
    supplier_indices: list[int] | None = None


class OutreachRetryFailedRequest(BaseModel):
    supplier_indices: list[int] | None = None


class OutreachCancelPendingRequest(BaseModel):
    supplier_indices: list[int] | None = None


class ClarifyingAnswerRequest(BaseModel):
    """User's answers to clarifying questions."""
    answers: dict[str, str] = Field(description="Mapping of field name to answer text")


class ProjectDecisionPreferenceRequest(BaseModel):
    lane_preference: Literal["best_overall", "best_low_risk", "best_speed_to_order"]


class ProjectRestartRequest(BaseModel):
    """Restart a project pipeline from parsing or discovery."""
    from_stage: str = Field(default="discovering", description="parsing or discovering")
    additional_context: str | None = Field(
        default=None,
        max_length=4000,
        description="Optional extra context to append before restarting",
    )


class PhoneCallStartRequest(BaseModel):
    """Request to initiate an AI phone call to a supplier."""
    supplier_index: int
    phone_number: str
    questions: list[str] = Field(default_factory=list)


class PhoneCallConfigRequest(BaseModel):
    """Configure AI phone calling for a project."""
    enabled: bool = False
    voice_id: str = "11labs-Adrian"
    max_call_duration_seconds: int = 300
    default_questions: list[str] = Field(default_factory=list)


# ── Procurement AI landing + growth endpoints ───────────────────────

class IntakeStartRequest(BaseModel):
    message: str = Field(min_length=10, max_length=5000)
    source: str = Field(default="landing_hero", max_length=120)
    session_id: str | None = Field(default=None, max_length=120)


class LeadCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=500)
    sourcing_note: str | None = Field(default=None, max_length=4000)
    source: str = Field(default="landing_early_access", max_length=120)


class AnalyticsEventRequest(BaseModel):
    event_name: str = Field(min_length=2, max_length=120)
    session_id: str | None = Field(default=None, max_length=120)
    path: str | None = Field(default=None, max_length=500)
    project_id: str | None = Field(default=None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
