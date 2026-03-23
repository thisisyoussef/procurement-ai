# Procurement AI

Procurement AI is an AI-assisted sourcing platform for finding, vetting, comparing, and contacting suppliers.

## Repository Layout
- `app/`: FastAPI backend, agents, persistence, and orchestration.
- `frontend/`: Next.js product and landing experience.
- `agentic_suite/`: External LangChain evaluation and continuous-improvement runner.
- `alembic/`: Database migrations.
- `tests/`: API and agent tests.
- `docs/`: Engineering plans, cleanup roadmap, and architecture notes.

## Core Runtime Flow
1. User creates a project from landing or product UI.
2. Backend pipeline parses requirements, discovers suppliers, verifies, compares, and recommends.
3. Outreach stage drafts/sends supplier emails with approval controls.
4. Project status and supplier interactions are persisted for memory reuse.

## Search Behavior
- `GET /api/v1/projects?q=...` and `GET /api/v1/dashboard/summary?q=...` match keywords against both project titles and product descriptions (case-insensitive).
- `GET /api/v1/dashboard/contacts?q=...` matches supplier keyword fragments against contact name, email, phone, website, city, and country (case-insensitive), with query filtering applied before result limiting so relevant matches are not dropped.
- `GET /api/v1/dashboard/activity` now falls back to per-project runtime timeline events (newest first) when DB-backed dashboard events are unavailable, while preserving `cursor` pagination semantics.
- Project status filters on `GET /api/v1/projects` and `GET /api/v1/dashboard/summary` accept repeated params (`?status=complete&status=failed`) and comma-separated lists (`?status=complete,failed`), including aliases `active` and `closed`.
- `POST /api/v1/projects/{id}/answer` now returns a safe `500` detail (`"Failed to process answers. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/dashboard/projects/start` normalizes `source` to supported dashboard entries (`dashboard_new`, `dashboard_search`) before telemetry/redirect attribution; unknown values default to `dashboard_new`.
- `POST /api/v1/projects/{id}/retrospective` is allowed only after the project is `complete`; otherwise the API returns `400` with `Retrospective can only be submitted for completed projects`.

## Local Development
- Backend: `uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Tests: `pytest`
- Frontend build: `cd frontend && npm run build`

## Documentation Index
- `docs/REFACTORING_PLAN.md`
- `docs/REFACTORING_TRACKER.md`
- `docs/AGENTIC_SUITE_PRD.md`
- Directory READMEs under `app/`, `frontend/src/`, `tests/`, and `alembic/`.

## Agent Merge Protocol
This repo uses short-lived feature branches that must be merged onto `main` before handing off work.

### Pre-merge checklist (before touching `main`)
1. Confirm you have no uncommitted local changes on your current branch.
2. Sync remote refs (`git fetch --all --prune`) and confirm branch ownership.
3. Validate branch scope in the PR body or branch name (one feature or one fix only).
4. Ensure feature code has passable tests where available (`pytest`, targeted frontend checks as relevant).
5. Rebase your feature branch onto latest `main` before merge.

### Merge process for agent handoff
1. Resolve local branch state: commit all changes and push branch.
2. Open or update PR from the feature branch into `main`.
3. Review diff for feature scope, migration impacts, and secret/config changes.
4. Merge with a merge commit unless the repo policy is to squash/rebase; do not squash when preserving per-feature history is required.
5. Run post-merge quick checks on `main` (`pytest`, API smoke checks, and frontend build).
6. Mark branch as merged and archive or delete local branch when approved.

### Emergency/cleanup policy
- If any feature branch is behind, behind-checkpoint required: rebase/merge `main`, rerun tests, and re-check conflicts.
- If you inherit an in-progress branch with missing commits, complete the work there and finalize in one commit before merge.
- If a merge introduces regression, revert only the merge commit and reopen the branch for corrective follow-up.

### Weekly consistency rule
Before every handoff, ensure all in-scope branches are either merged into `main` or explicitly closed with a reason in the PR/repo tracker.
