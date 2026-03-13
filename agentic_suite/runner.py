"""End-to-end run execution (real backend mode and dry-run mode)."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any

from .api_client import BackendClient
from .config import SuiteSettings
from .models import RunArtifact, RunMetrics, RunScenario, StageSnapshot


class ScenarioRunner:
    """Executes one scenario run and captures complete telemetry."""

    def __init__(
        self,
        *,
        settings: SuiteSettings,
        client: BackendClient | None,
        clarification_agent,
    ) -> None:
        self.settings = settings
        self.client = client
        self.clarification_agent = clarification_agent

    async def run_once(self, *, suite_id: str, run_index: int, scenario: RunScenario) -> RunArtifact:
        if self.settings.dry_run:
            return self._run_simulated(suite_id=suite_id, run_index=run_index, scenario=scenario)
        if self.client is None:
            raise RuntimeError("Backend client is required when dry_run is disabled")
        return await self._run_against_backend(suite_id=suite_id, run_index=run_index, scenario=scenario)

    async def _run_against_backend(
        self,
        *,
        suite_id: str,
        run_index: int,
        scenario: RunScenario,
    ) -> RunArtifact:
        assert self.client is not None

        run_id = f"run-{run_index:02d}"
        started_at = time.time()
        project = await self.client.create_project(
            title=f"[AgenticSuite] {scenario.title}",
            product_description=scenario.product_description,
            auto_outreach=scenario.auto_outreach or self.settings.auto_outreach,
        )
        project_id = str(project.get("project_id"))

        stage_trace: list[StageSnapshot] = []
        final_status: dict[str, Any] = {}
        clarifying_round_trips = 0
        restart_attempts = 0
        interruption_reason: str | None = None

        while True:
            elapsed = time.time() - started_at
            if elapsed > self.settings.run_timeout_seconds:
                interruption_reason = "timeout"
                try:
                    await self.client.cancel_project(project_id)
                except Exception:  # noqa: BLE001
                    pass
                break

            status = await self.client.get_project_status(project_id)
            final_status = status

            self._append_stage_trace(stage_trace, status)

            current_status = str(status.get("status") or "")
            current_stage = str(status.get("current_stage") or current_status)

            if current_stage == "clarifying":
                questions = status.get("clarifying_questions") or []
                if questions and clarifying_round_trips < self.settings.max_clarification_round_trips:
                    answers = await self.clarification_agent.answer_questions(
                        scenario=scenario,
                        questions=questions,
                        parsed_requirements=status.get("parsed_requirements"),
                    )
                    if answers:
                        await self.client.answer_clarifying_questions(project_id=project_id, answers=answers)
                        clarifying_round_trips += 1
                        await asyncio.sleep(self.settings.poll_interval_seconds)
                        continue

                # If we cannot answer further, keep progress moving by skipping.
                if questions:
                    await self.client.skip_clarifying_questions(project_id)
                    clarifying_round_trips += 1

            if current_status in {"complete", "canceled"}:
                break

            if current_status == "failed":
                if restart_attempts < self.settings.max_restart_attempts:
                    restart_attempts += 1
                    await self.client.restart_project(
                        project_id=project_id,
                        from_stage="parsing",
                        additional_context=self._restart_context(final_status),
                    )
                else:
                    break

            await asyncio.sleep(self.settings.poll_interval_seconds)

        try:
            logs = await self.client.get_project_logs(project_id)
        except Exception:  # noqa: BLE001
            logs = []
        if self.settings.keep_log_entries > 0:
            logs = logs[-self.settings.keep_log_entries :]

        ended_at = time.time()
        metrics = self._build_metrics(
            final_status=final_status,
            logs=logs,
            started_at=started_at,
            ended_at=ended_at,
            interruption_reason=interruption_reason,
            clarifying_round_trips=clarifying_round_trips,
            restart_attempts=restart_attempts,
        )

        return RunArtifact(
            suite_id=suite_id,
            run_id=run_id,
            run_index=run_index,
            scenario=scenario,
            project_id=project_id,
            started_at=started_at,
            ended_at=ended_at,
            stage_trace=stage_trace,
            final_status_payload=final_status,
            logs=logs,
            metrics=metrics,
        )

    def _run_simulated(self, *, suite_id: str, run_index: int, scenario: RunScenario) -> RunArtifact:
        seed = f"{suite_id}:{run_index}:{scenario.scenario_id}"
        rnd = random.Random(seed)

        started_at = time.time()
        duration = rnd.uniform(15, 75)
        success = rnd.random() > 0.25
        interrupted = rnd.random() < 0.1

        discovered = rnd.randint(6, 22)
        verified = rnd.randint(3, min(discovered, 18))
        recommended = rnd.randint(1, min(verified, 5)) if success else rnd.randint(0, 2)
        terminal_status = "complete" if success else ("failed" if not interrupted else "canceled")
        terminal_stage = "complete" if success else rnd.choice(["discovering", "verifying", "comparing", "recommending"])
        error = None if success else "simulated failure: schema mismatch in downstream stage"

        final_status = {
            "status": terminal_status,
            "current_stage": terminal_stage,
            "error": error,
            "discovery_results": {"suppliers": [{}] * discovered},
            "verification_results": {"verifications": [{}] * verified},
            "recommendation": {"recommendations": [{}] * recommended},
            "progress_events": [{}] * rnd.randint(8, 28),
        }
        stage_trace = [
            StageSnapshot(stage="parsing", status="parsing", timestamp=started_at),
            StageSnapshot(stage="discovering", status="discovering", timestamp=started_at + 2),
            StageSnapshot(stage=terminal_stage, status=terminal_status, timestamp=started_at + duration, error=error),
        ]
        logs = [
            {"level": "INFO", "logger": "agents.orchestrator", "message": "Simulated run started", "ts": started_at},
            {
                "level": "ERROR" if error else "INFO",
                "logger": "agents.orchestrator",
                "message": error or "Simulated run complete",
                "ts": started_at + duration,
            },
        ]

        metrics = RunMetrics(
            success=success,
            terminal_status=terminal_status,
            terminal_stage=terminal_stage,
            duration_seconds=duration,
            interrupted=interrupted,
            interruption_reason="timeout" if interrupted else None,
            restart_attempts=0,
            clarifying_round_trips=rnd.randint(0, 1),
            discovered_suppliers=discovered,
            verified_suppliers=verified,
            recommended_suppliers=recommended,
            progress_event_count=len(final_status["progress_events"]),
            log_count=len(logs),
            failure_mode=error,
        )

        ended_at = started_at + duration
        return RunArtifact(
            suite_id=suite_id,
            run_id=f"run-{run_index:02d}",
            run_index=run_index,
            scenario=scenario,
            project_id=f"sim-{run_index:02d}",
            started_at=started_at,
            ended_at=ended_at,
            stage_trace=stage_trace,
            final_status_payload=final_status,
            logs=logs,
            metrics=metrics,
        )

    @staticmethod
    def _append_stage_trace(stage_trace: list[StageSnapshot], status: dict[str, Any]) -> None:
        stage = str(status.get("current_stage") or status.get("status") or "unknown")
        run_status = str(status.get("status") or "unknown")
        error = status.get("error")

        if stage_trace:
            last = stage_trace[-1]
            if last.stage == stage and last.status == run_status and last.error == error:
                return

        stage_trace.append(StageSnapshot(stage=stage, status=run_status, error=error))

    @staticmethod
    def _restart_context(status: dict[str, Any]) -> str:
        error = str(status.get("error") or "")[:300]
        return (
            "Automatic retry from agentic suite. Preserve intent, tighten schema compliance, "
            "and avoid dropping all suppliers during verification/comparison. "
            f"Previous failure: {error}"
        )

    @staticmethod
    def _build_metrics(
        *,
        final_status: dict[str, Any],
        logs: list[dict[str, Any]],
        started_at: float,
        ended_at: float,
        interruption_reason: str | None,
        clarifying_round_trips: int,
        restart_attempts: int,
    ) -> RunMetrics:
        terminal_status = str(final_status.get("status") or "unknown")
        terminal_stage = str(final_status.get("current_stage") or terminal_status)
        discovery_results = final_status.get("discovery_results") or {}
        verification_results = final_status.get("verification_results") or {}
        recommendation = final_status.get("recommendation") or {}

        discovered = len(discovery_results.get("suppliers") or [])
        verified = len(verification_results.get("verifications") or [])
        recommended = len(recommendation.get("recommendations") or [])
        progress_event_count = len(final_status.get("progress_events") or [])

        error = final_status.get("error")
        failure_mode = str(error)[:240] if error else None

        return RunMetrics(
            success=terminal_status == "complete",
            terminal_status=terminal_status,
            terminal_stage=terminal_stage,
            duration_seconds=max(0.0, ended_at - started_at),
            interrupted=interruption_reason is not None,
            interruption_reason=interruption_reason,
            restart_attempts=restart_attempts,
            clarifying_round_trips=clarifying_round_trips,
            discovered_suppliers=discovered,
            verified_suppliers=verified,
            recommended_suppliers=recommended,
            progress_event_count=progress_event_count,
            log_count=len(logs),
            failure_mode=failure_mode,
        )

