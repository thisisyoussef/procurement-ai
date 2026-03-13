"""Aggregate multi-run results into suite-level statistics."""

from __future__ import annotations

import statistics
from collections import Counter

from .models import AggregateReport, FrequencyItem, RunArtifact


def _counter_to_items(counter: Counter[str], limit: int = 8) -> list[FrequencyItem]:
    return [FrequencyItem(item=item, count=count) for item, count in counter.most_common(limit)]


def build_aggregate_report(*, suite_id: str, artifacts: list[RunArtifact]) -> AggregateReport:
    total_runs = len(artifacts)
    if total_runs == 0:
        return AggregateReport(
            suite_id=suite_id,
            total_runs=0,
            successful_runs=0,
            interrupted_runs=0,
            success_rate=0.0,
            avg_duration_seconds=0.0,
            median_duration_seconds=0.0,
        )

    successful_runs = sum(1 for artifact in artifacts if artifact.metrics.success)
    interrupted_runs = sum(1 for artifact in artifacts if artifact.metrics.interrupted)
    durations = [artifact.metrics.duration_seconds for artifact in artifacts]

    stage_dropoff_counter: Counter[str] = Counter()
    failure_mode_counter: Counter[str] = Counter()

    for artifact in artifacts:
        stage_dropoff_counter.update([artifact.metrics.terminal_stage or "unknown"])
        if artifact.metrics.failure_mode:
            failure_mode_counter.update([artifact.metrics.failure_mode])

    return AggregateReport(
        suite_id=suite_id,
        total_runs=total_runs,
        successful_runs=successful_runs,
        interrupted_runs=interrupted_runs,
        success_rate=successful_runs / total_runs,
        avg_duration_seconds=float(statistics.fmean(durations)),
        median_duration_seconds=float(statistics.median(durations)),
        stage_dropoff=_counter_to_items(stage_dropoff_counter),
        failure_modes=_counter_to_items(failure_mode_counter),
    )

