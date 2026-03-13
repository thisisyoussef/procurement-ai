"""CLI entrypoint for running 5-10 end-to-end agentic evaluation runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agents import AggregateAgent, ClarificationAgent, CriticAgent, PRDWriterAgent
from .aggregate import build_aggregate_report
from .api_client import BackendClient
from .config import SuiteSettings
from .llm import build_chat_model
from .models import RunArtifact, RunMetrics, RunScenario
from .prd import render_prd_markdown


def _json_dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True, default=str)


def _load_scenarios(scenario_file: str | None) -> list[RunScenario]:
    if scenario_file:
        raw = Path(scenario_file).expanduser().resolve().read_text(encoding="utf-8")
    else:
        bundled = Path(__file__).resolve().parent / "scenarios" / "default_scenarios.json"
        raw = bundled.read_text(encoding="utf-8")

    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("Scenario file must contain a JSON array")

    scenarios = [RunScenario.model_validate(item) for item in payload]
    if not scenarios:
        raise ValueError("At least one scenario is required")
    return scenarios


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the external LangChain agentic suite")
    parser.add_argument("--runs", type=int, default=None, help="Number of runs (5-10)")
    parser.add_argument("--base-url", type=str, default=None, help="Backend base URL")
    parser.add_argument("--scenario-file", type=str, default=None, help="Scenario JSON file path")
    parser.add_argument("--output-root", type=str, default=None, help="Output root directory")
    parser.add_argument("--dry-run", action="store_true", help="Run without backend calls")
    parser.add_argument("--auto-outreach", action="store_true", help="Enable auto outreach")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="Per-run timeout")
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable LLM usage and use heuristic agents only",
    )
    return parser.parse_args(argv)


async def _run_suite(
    *,
    settings: SuiteSettings,
    scenarios: list[RunScenario],
    runs: int,
    output_dir: Path,
) -> dict[str, Any]:
    suite_id = output_dir.name

    llm = build_chat_model(settings)
    if settings.llm_enabled and llm is None:
        print("[agentic-suite] LLM unavailable, falling back to heuristic critique/synthesis")

    clarifier = ClarificationAgent(llm)
    critic = CriticAgent(llm)
    aggregate_agent = AggregateAgent(llm)
    prd_writer = PRDWriterAgent(llm)

    run_artifacts: list[RunArtifact] = []
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    async def run_single(index: int, runner) -> None:
        scenario = scenarios[(index - 1) % len(scenarios)]
        started_at = time.time()
        try:
            artifact = await runner.run_once(suite_id=suite_id, run_index=index, scenario=scenario)
        except Exception as exc:  # noqa: BLE001
            ended_at = time.time()
            error_text = str(exc)
            artifact = RunArtifact(
                suite_id=suite_id,
                run_id=f"run-{index:02d}",
                run_index=index,
                scenario=scenario,
                project_id=None,
                started_at=started_at,
                ended_at=ended_at,
                stage_trace=[],
                final_status_payload={"status": "failed", "error": error_text},
                logs=[],
                metrics=RunMetrics(
                    success=False,
                    terminal_status="failed",
                    terminal_stage="failed",
                    duration_seconds=max(0.0, ended_at - started_at),
                    interrupted=False,
                    interruption_reason=None,
                    restart_attempts=0,
                    clarifying_round_trips=0,
                    discovered_suppliers=0,
                    verified_suppliers=0,
                    recommended_suppliers=0,
                    progress_event_count=0,
                    log_count=0,
                    failure_mode=error_text[:240],
                ),
            )
        artifact.critique = await critic.critique(artifact)
        run_artifacts.append(artifact)

        artifact_path = runs_dir / f"{artifact.run_id}.json"
        artifact_path.write_text(_json_dumps(artifact.model_dump(mode="json")), encoding="utf-8")

        print(
            "[agentic-suite] "
            f"{artifact.run_id} status={artifact.metrics.terminal_status} "
            f"stage={artifact.metrics.terminal_stage} "
            f"score={artifact.critique.overall_score if artifact.critique else 0:.1f}"
        )

    if settings.dry_run:
        from .runner import ScenarioRunner

        runner = ScenarioRunner(settings=settings, client=None, clarification_agent=clarifier)
        for index in range(1, runs + 1):
            await run_single(index, runner)
    else:
        token = settings.resolve_access_token()
        if not token:
            raise RuntimeError(
                "No auth token available. Set AGENTIC_ACCESS_TOKEN or APP_SECRET_KEY/AGENTIC_APP_SECRET_KEY."
            )

        async with BackendClient(
            base_url=settings.api_base_url,
            access_token=token,
            timeout_seconds=settings.request_timeout_seconds,
        ) as client:
            await client.health_check()

            from .runner import ScenarioRunner

            runner = ScenarioRunner(settings=settings, client=client, clarification_agent=clarifier)
            for index in range(1, runs + 1):
                await run_single(index, runner)

    run_artifacts.sort(key=lambda item: item.run_index)

    report = build_aggregate_report(suite_id=suite_id, artifacts=run_artifacts)
    synthesis = await aggregate_agent.synthesize(report=report, artifacts=run_artifacts)
    report.synthesis = synthesis

    prd_doc = await prd_writer.write_prd(report=report, synthesis=synthesis, artifacts=run_artifacts)
    prd_markdown = render_prd_markdown(prd=prd_doc, report=report, artifacts=run_artifacts)

    aggregate_path = output_dir / "aggregate_report.json"
    aggregate_path.write_text(_json_dumps(report.model_dump(mode="json")), encoding="utf-8")

    prd_json_path = output_dir / "prd_structured.json"
    prd_json_path.write_text(_json_dumps(prd_doc.model_dump(mode="json")), encoding="utf-8")

    prd_md_path = output_dir / "PRD_AGENTIC_SUITE.md"
    prd_md_path.write_text(prd_markdown, encoding="utf-8")

    manifest = {
        "suite_id": suite_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run" if settings.dry_run else "live_backend",
        "runs": runs,
        "api_base_url": settings.api_base_url,
        "scenario_ids": [s.scenario_id for s in scenarios],
        "files": {
            "aggregate_report": str(aggregate_path),
            "prd_structured": str(prd_json_path),
            "prd_markdown": str(prd_md_path),
            "runs_dir": str(runs_dir),
        },
    }
    (output_dir / "suite_manifest.json").write_text(_json_dumps(manifest), encoding="utf-8")

    return manifest


def _apply_cli_overrides(settings: SuiteSettings, args: argparse.Namespace) -> tuple[SuiteSettings, int]:
    if args.base_url:
        settings.api_base_url = args.base_url
    if args.scenario_file:
        settings.scenario_file = args.scenario_file
    if args.output_root:
        settings.output_root = args.output_root
    if args.dry_run:
        settings.dry_run = True
    if args.auto_outreach:
        settings.auto_outreach = True
    if args.timeout_seconds is not None:
        settings.run_timeout_seconds = args.timeout_seconds
    if args.disable_llm:
        settings.llm_enabled = False

    runs = args.runs if args.runs is not None else settings.runs
    runs = settings.validate_runs(runs)
    return settings, runs


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = SuiteSettings()
    settings, runs = _apply_cli_overrides(settings, args)

    scenarios = _load_scenarios(settings.scenario_file)

    suite_id = datetime.now(timezone.utc).strftime("suite_%Y%m%d_%H%M%S")
    output_dir = settings.output_root_path / suite_id
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()
    manifest = asyncio.run(
        _run_suite(
            settings=settings,
            scenarios=scenarios,
            runs=runs,
            output_dir=output_dir,
        )
    )
    elapsed = time.time() - start

    print("[agentic-suite] complete")
    print(f"[agentic-suite] suite_id={manifest['suite_id']}")
    print(f"[agentic-suite] mode={manifest['mode']}")
    print(f"[agentic-suite] runs={manifest['runs']}")
    print(f"[agentic-suite] elapsed={elapsed:.1f}s")
    print(f"[agentic-suite] manifest={output_dir / 'suite_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
