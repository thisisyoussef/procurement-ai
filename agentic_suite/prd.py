"""PRD markdown rendering from structured suite output."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import fmean

from .models import AggregateReport, PRDDocument, RunArtifact


def _fmt_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _fmt_seconds(value: float) -> str:
    return f"{value:.1f}s"


def _is_simulation_run(artifacts: list[RunArtifact]) -> bool:
    if not artifacts:
        return False
    return all(str(a.project_id or "").startswith("sim-") for a in artifacts)


def _safe_mean(values: list[float]) -> float:
    return float(fmean(values)) if values else 0.0


def _scenario_label(artifact: RunArtifact) -> str:
    return artifact.scenario.title.strip() or artifact.run_id


def _extract_observations(artifacts: list[RunArtifact]) -> list[str]:
    total = len(artifacts)
    if total == 0:
        return []

    clarify_runs = sum(1 for a in artifacts if a.metrics.clarifying_round_trips > 0)
    thin_shortlist_runs = sum(1 for a in artifacts if a.metrics.recommended_suppliers <= 2)
    heavy_filter_runs = sum(
        1
        for a in artifacts
        if (a.metrics.discovered_suppliers >= 10 and a.metrics.recommended_suppliers <= 2)
    )
    long_runs = sum(1 for a in artifacts if a.metrics.duration_seconds >= 60)
    interrupted_runs = sum(1 for a in artifacts if a.metrics.interrupted)

    observations: list[str] = []
    observations.append(
        "The flow tends to build momentum early (brief -> search), but confidence can drop at recommendation time when shortlist breadth shrinks suddenly."
    )
    observations.append(
        f"In {thin_shortlist_runs}/{total} runs, the final shortlist contained 2 or fewer recommendations, which can feel like over-filtering even when discovery found many options."
    )
    if clarify_runs > 0:
        observations.append(
            f"Clarifying questions appeared in {clarify_runs}/{total} runs; this is useful, but users need explicit context for why the question matters right now."
        )
    if heavy_filter_runs > 0:
        observations.append(
            f"{heavy_filter_runs}/{total} runs showed a high discovery-to-recommendation drop, suggesting we need better explanation of elimination logic."
        )
    if long_runs > 0:
        observations.append(
            f"{long_runs}/{total} runs lasted 60s or longer; when runs are long, we should communicate expected wait and decision progress, not only pipeline stage."
        )
    if interrupted_runs > 0:
        observations.append(
            f"{interrupted_runs}/{total} runs registered interruption signals, so status messaging should clearly distinguish system timeout from user cancel and completion."
        )

    return observations


def _session_vignettes(artifacts: list[RunArtifact], max_items: int = 5) -> list[str]:
    vignettes: list[str] = []
    for artifact in artifacts[:max_items]:
        m = artifact.metrics
        vignettes.append(
            (
                f"{_scenario_label(artifact)}: discovered {m.discovered_suppliers}, "
                f"verified {m.verified_suppliers}, recommended {m.recommended_suppliers}, "
                f"duration {_fmt_seconds(m.duration_seconds)}."
            )
        )
    return vignettes


def _top_initiatives(prd: PRDDocument, limit: int = 6) -> list[str]:
    items: list[str] = []
    for ws in prd.workstreams:
        for initiative in ws.initiatives:
            items.append(f"{ws.priority}: {initiative}")
    return items[:limit]


def render_prd_markdown(
    *,
    prd: PRDDocument,
    report: AggregateReport,
    artifacts: list[RunArtifact],
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    success_rate = _fmt_percent(report.success_rate)
    avg_duration = _fmt_seconds(report.avg_duration_seconds)
    median_duration = _fmt_seconds(report.median_duration_seconds)
    simulation = _is_simulation_run(artifacts)

    recommendation_counts = [a.metrics.recommended_suppliers for a in artifacts]
    discovered_counts = [a.metrics.discovered_suppliers for a in artifacts]
    verified_counts = [a.metrics.verified_suppliers for a in artifacts]
    critique_scores = [a.critique.overall_score for a in artifacts if a.critique]

    lines: list[str] = []
    lines.append("# PRD: Improve the Product Search Experience (Focus-Circle Synthesis)")
    lines.append("")
    lines.append(f"Date: {generated_at}")
    lines.append(f"Source: {report.total_runs} end-to-end runs from `{report.suite_id}`")
    if simulation:
        lines.append("Evidence mode: simulation-based proxy sessions")
    else:
        lines.append("Evidence mode: live backend sessions")
    lines.append("")

    lines.append("## Why This Exists")
    lines.append(prd.context or "This document captures qualitative learning from repeated end-to-end sourcing sessions.")
    lines.append("")

    lines.append("## What People Tried to Do")
    lines.append("Across scenarios, users followed the same intent:")
    lines.append("- Start with an imperfect brief.")
    lines.append("- Let the system carry most of the sourcing workload.")
    lines.append("- Reach a shortlist they can defend to internal stakeholders.")
    lines.append("")

    lines.append("## What We Observed")
    for idx, observation in enumerate(_extract_observations(artifacts), start=1):
        lines.append(f"### {idx}. {observation}")
        lines.append("")

    lines.append("## Session Snapshots")
    for vignette in _session_vignettes(artifacts):
        lines.append(f"- {vignette}")
    lines.append("")

    lines.append("## Product Intent vs Reality")
    lines.append(f'- Intended: "{prd.north_star or "Fast, trustworthy sourcing decisions with clear rationale."}"')
    lines.append("- Observed: users get movement and data, but confidence can weaken when recommendation narrowing is not explained in human terms.")
    lines.append("")

    lines.append("## Ground Truth From Runs")
    lines.append(f"- Total runs: {report.total_runs}")
    lines.append(f"- Successful runs: {report.successful_runs}")
    lines.append(f"- Interrupted runs: {report.interrupted_runs}")
    lines.append(f"- Success rate: {success_rate}")
    lines.append(f"- Average duration: {avg_duration}")
    lines.append(f"- Median duration: {median_duration}")
    if discovered_counts:
        lines.append(f"- Avg discovered suppliers: {_safe_mean([float(v) for v in discovered_counts]):.1f}")
    if verified_counts:
        lines.append(f"- Avg verified suppliers: {_safe_mean([float(v) for v in verified_counts]):.1f}")
    if recommendation_counts:
        lines.append(f"- Avg recommended suppliers: {_safe_mean([float(v) for v in recommendation_counts]):.1f}")
    if critique_scores:
        lines.append(f"- Avg critique score: {_safe_mean(critique_scores):.1f}/100")
    lines.append("")

    lines.append("## Product Requirements (Qualitative First)")
    lines.append("### A. Decision Confidence Layer")
    lines.append("- Add a `Why these suppliers` section before final recommendations.")
    lines.append("- Show confidence bands, evidence highlights, and explicit uncertainty.")
    lines.append("- Explain when and why strong candidates were filtered out.")
    lines.append("")

    lines.append("### B. Clarification UX Upgrade")
    lines.append("- For each question, show `why it matters now` and `what happens if skipped`.")
    lines.append("- Provide a suggested default answer to reduce interruption friction.")
    lines.append("- Keep clarification as coaching, not a blocking detour.")
    lines.append("")

    lines.append("### C. Recommendation Explanation Policy")
    lines.append("- Aim to provide multiple recommendation lanes (best overall, low-risk, speed).")
    lines.append("- If fewer lanes are available, say exactly why in plain language.")
    lines.append("- Attach a `verify before PO` checklist to each top supplier.")
    lines.append("")

    lines.append("### D. Decision-Progress Timeline")
    lines.append("- Progress feed should report decision readiness, not only pipeline stage.")
    lines.append("- Add milestones like `confidence established` and `ready for outreach decision`.")
    lines.append("- Set expectations when a run is likely to take longer.")
    lines.append("")

    lines.append("## Prompt and Flow Changes to Ship")
    for initiative in _top_initiatives(prd):
        lines.append(f"- {initiative}")
    lines.append("")

    if report.synthesis and report.synthesis.priority_actions:
        lines.append("## Priority Actions from Test Debrief")
        for action in report.synthesis.priority_actions:
            lines.append(f"- {action}")
        lines.append("")

    lines.append("## Success Criteria for Next Focus Circle")
    for metric in prd.success_metrics:
        lines.append(f"- {metric}")
    lines.append("")

    lines.append("## Workstreams")
    for ws in prd.workstreams:
        lines.append(f"### {ws.name} ({ws.priority})")
        lines.append(f"- Objective: {ws.objective}")
        lines.append(f"- Owner: {ws.owner}")
        lines.append(f"- Window: {ws.release_window}")
        for initiative in ws.initiatives:
            lines.append(f"- {initiative}")
        lines.append("")

    lines.append("## Experiment Plan")
    for experiment in prd.experiments:
        lines.append(f"- {experiment}")
    lines.append("")

    lines.append("## Rollout Guardrails")
    for guardrail in prd.rollout_guardrails:
        lines.append(f"- {guardrail}")
    lines.append("")

    lines.append("## Open Questions")
    for question in prd.open_questions:
        lines.append(f"- {question}")
    lines.append("")

    lines.append("## Run Appendix")
    for artifact in artifacts:
        lines.append(f"### {artifact.run_id} - {artifact.scenario.title}")
        lines.append(f"- Project ID: {artifact.project_id}")
        lines.append(f"- Terminal status: {artifact.metrics.terminal_status}")
        lines.append(f"- Terminal stage: {artifact.metrics.terminal_stage}")
        lines.append(f"- Duration: {_fmt_seconds(artifact.metrics.duration_seconds)}")
        lines.append(
            "- Suppliers discovered / verified / recommended: "
            f"{artifact.metrics.discovered_suppliers} / {artifact.metrics.verified_suppliers} / {artifact.metrics.recommended_suppliers}"
        )
        if artifact.critique:
            lines.append(f"- Critique score: {artifact.critique.overall_score:.1f}")
            if artifact.critique.issues:
                lines.append(f"- Key issue: {artifact.critique.issues[0]}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
