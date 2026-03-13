"""Typed contracts for scenarios, run artifacts, synthesis, and PRD output."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field


class RunScenario(BaseModel):
    scenario_id: str
    title: str
    product_description: str
    auto_outreach: bool = False
    notes: str | None = None
    expected_focus: list[str] = Field(default_factory=list)


class StageSnapshot(BaseModel):
    stage: str
    status: str
    timestamp: float = Field(default_factory=time.time)
    error: str | None = None


class RunMetrics(BaseModel):
    success: bool = False
    terminal_status: str = "unknown"
    terminal_stage: str = "unknown"
    duration_seconds: float = 0.0
    interrupted: bool = False
    interruption_reason: str | None = None
    restart_attempts: int = 0
    clarifying_round_trips: int = 0
    discovered_suppliers: int = 0
    verified_suppliers: int = 0
    recommended_suppliers: int = 0
    progress_event_count: int = 0
    log_count: int = 0
    failure_mode: str | None = None


class RunCritique(BaseModel):
    overall_score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class RunArtifact(BaseModel):
    suite_id: str
    run_id: str
    run_index: int
    scenario: RunScenario
    project_id: str | None = None
    started_at: float
    ended_at: float
    stage_trace: list[StageSnapshot] = Field(default_factory=list)
    final_status_payload: dict[str, Any] = Field(default_factory=dict)
    logs: list[dict[str, Any]] = Field(default_factory=list)
    metrics: RunMetrics
    critique: RunCritique | None = None


class FrequencyItem(BaseModel):
    item: str
    count: int


class AggregateSynthesis(BaseModel):
    recurring_issues: list[FrequencyItem] = Field(default_factory=list)
    recurring_strengths: list[FrequencyItem] = Field(default_factory=list)
    priority_actions: list[str] = Field(default_factory=list)


class AggregateReport(BaseModel):
    suite_id: str
    generated_at: float = Field(default_factory=time.time)
    total_runs: int
    successful_runs: int
    interrupted_runs: int
    success_rate: float
    avg_duration_seconds: float
    median_duration_seconds: float
    stage_dropoff: list[FrequencyItem] = Field(default_factory=list)
    failure_modes: list[FrequencyItem] = Field(default_factory=list)
    synthesis: AggregateSynthesis | None = None


class PRDWorkstream(BaseModel):
    name: str
    priority: str
    objective: str
    initiatives: list[str] = Field(default_factory=list)
    owner: str = "Platform + Backend + AI"
    release_window: str = "TBD"


class PRDDocument(BaseModel):
    title: str
    context: str
    north_star: str
    success_metrics: list[str] = Field(default_factory=list)
    workstreams: list[PRDWorkstream] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)
    rollout_guardrails: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

