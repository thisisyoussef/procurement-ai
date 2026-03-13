# Agentic Suite (External Layer)

This package is a separate, API-driven evaluation and improvement layer for Procurement AI.
It does not import runtime pipeline internals from `app/`; it drives the product through backend HTTP endpoints.

## What It Does

1. Runs 5-10 full sourcing scenarios end-to-end via `/api/v1/projects`.
2. Handles clarifying questions automatically to continue runs.
3. Polls status until completion, failure, cancellation, or timeout interruption.
4. Captures logs and status payloads for each run.
5. Produces run-level critique and cross-run synthesis.
6. Generates an implementation PRD for continuous product improvement.

## Key Components

- `agentic_suite/api_client.py`: Backend API adapter.
- `agentic_suite/runner.py`: End-to-end run loop (live + dry-run).
- `agentic_suite/agents.py`: LangChain agents (clarifier, critic, synthesis, PRD writer).
- `agentic_suite/aggregate.py`: Suite-level metrics aggregation.
- `agentic_suite/prd.py`: PRD markdown rendering.
- `agentic_suite/cli.py`: CLI orchestration entrypoint.
- `agentic_suite/prompts/*.md`: Prompt templates.
- `agentic_suite/scenarios/default_scenarios.json`: Canonical run scenarios.

## Auth

The suite supports either:
- `AGENTIC_ACCESS_TOKEN` (preferred), or
- Local token signing via `APP_SECRET_KEY` / `AGENTIC_APP_SECRET_KEY` and `AGENTIC_DEV_USER_ID`.

## Run

Live backend mode:

```bash
python -m agentic_suite --runs 5 --base-url http://localhost:8000
```

Dry-run mode (no backend required):

```bash
python -m agentic_suite --runs 5 --dry-run
```

Disable LLM (heuristic critique/synthesis/PRD):

```bash
python -m agentic_suite --runs 5 --disable-llm
```

## Output

Each suite run writes to `agentic_suite_outputs/<suite_id>/`:

- `runs/run-XX.json` (raw artifact + critique)
- `aggregate_report.json`
- `prd_structured.json`
- `PRD_AGENTIC_SUITE.md`
- `suite_manifest.json`

## Notes

- `--runs` is constrained to 5-10 by design for consistent comparison.
- Use `AGENTIC_SCENARIO_FILE` or `--scenario-file` to test custom scenario sets.
