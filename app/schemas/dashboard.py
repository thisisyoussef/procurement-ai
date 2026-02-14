"""Dashboard API request/response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class DashboardGreeting(BaseModel):
    time_label: str
    user_first_name: str
    active_projects: int
    headline: str
    body: str


class DashboardAttentionItem(BaseModel):
    id: str
    kind: str
    priority: str = "medium"
    title: str
    subtitle: str
    project_id: str
    cta: str
    target_phase: str | None = None


class DashboardProjectStats(BaseModel):
    quotes_count: int = 0
    best_price: str | None = None
    samples_sent: int = 0


class DashboardProjectCard(BaseModel):
    id: str
    name: str
    description: str
    phase_label: str
    status: str
    progress_step: int
    progress_total: int = 6
    stats: DashboardProjectStats
    status_note: str
    visual_variant: int = 1


class DashboardActivityItem(BaseModel):
    id: str
    at: float
    time_label: str
    title: str
    description: str
    project_id: str | None = None
    project_name: str | None = None
    type: str
    priority: str = "info"
    payload: dict[str, Any] = Field(default_factory=dict)


class DashboardSummaryResponse(BaseModel):
    greeting: DashboardGreeting
    attention: list[DashboardAttentionItem] = Field(default_factory=list)
    projects: list[DashboardProjectCard] = Field(default_factory=list)
    recent_activity: list[DashboardActivityItem] = Field(default_factory=list)


class DashboardActivityResponse(BaseModel):
    events: list[DashboardActivityItem] = Field(default_factory=list)
    next_cursor: str | None = None


class DashboardProjectStartRequest(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    auto_outreach: bool = False
    source: str = Field(default="dashboard_new", max_length=120)


class DashboardProjectStartResponse(BaseModel):
    project_id: str
    status: str
    redirect_path: str


class DashboardSupplierContact(BaseModel):
    supplier_id: str
    name: str
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    interaction_count: int
    project_count: int
    last_interaction_at: float | None = None
    last_project_id: str | None = None


class DashboardContactsResponse(BaseModel):
    suppliers: list[DashboardSupplierContact] = Field(default_factory=list)
    count: int = 0
