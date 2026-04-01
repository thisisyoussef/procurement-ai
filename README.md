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
- `GET /api/v1/dashboard/summary` scopes `recent_activity` to the same filtered project set when `status` and/or `q` filters are supplied, so cards and activity stay aligned.
- `GET /api/v1/dashboard/contacts?q=...` matches supplier keyword fragments against contact name, email, phone, website, city, country, and associated project title/description (case-insensitive), including digit-only phone lookup against formatted numbers (for example `3125550142` matches `+1 (312) 555-0142`); multi-term queries (for example `bottle detroit`) require all terms to match across those fields, and filtering is applied before result limiting so relevant matches are not dropped.
- `GET /api/v1/dashboard/contacts` accepts project status filters via repeated params (`?status=discovering&status=complete`) or comma-separated lists (`?status=discovering,complete`), including aliases `active` and `closed`; when set, contacts are scoped to projects in those statuses.
- `GET /api/v1/dashboard/contacts?q=...` non-empty queries must be at least 2 characters (whitespace-only still behaves as no filter).
- `GET /api/v1/dashboard/contacts` merges DB-backed supplier contacts with runtime project discovery contacts (deduplicated), ensuring newly discovered suppliers still appear even when they have no DB interaction rows yet; query filtering remains applied before response limiting.
- `GET /api/v1/dashboard/activity` now falls back to per-project runtime timeline events (newest first) when DB-backed dashboard events are unavailable, while preserving `cursor` pagination semantics.
- `GET /api/v1/dashboard/summary`, `GET /api/v1/dashboard/activity`, `GET /api/v1/dashboard/contacts`, and `POST /api/v1/dashboard/projects/start` now return a safe `503` detail (`"Dashboard is temporarily unavailable. Please try again."`) when project storage is unavailable, without exposing backend exception text.
- Project status filters on `GET /api/v1/projects` and `GET /api/v1/dashboard/summary` accept repeated params (`?status=complete&status=failed`) and comma-separated lists (`?status=complete,failed`), including aliases `active` and `closed`.
- Project list and dashboard summary status handling now fall back to canonical `current_stage` when legacy records have blank `status`, so active/closed filters and active counts remain accurate.
- `POST /api/v1/projects/{id}/answer` now returns a safe `500` detail (`"Failed to process answers. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/search` now returns a safe `500` detail (`"Failed to run quick search. Please try again."`) for unexpected failures, without exposing internal exception strings.
- Project store failures on `POST /api/v1/projects`, `GET /api/v1/projects`, and `GET /api/v1/projects/{id}/status` now return a safe `503` detail (`"Project service is temporarily unavailable. Please try again."`) without exposing backend exception text.
- `POST /api/v1/projects/{id}/outreach/start` now returns a safe `500` detail (`"Failed to start outreach. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/{id}/outreach/parse-response` now returns a safe `500` detail (`"Failed to parse outreach response. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/{id}/outreach/follow-up` now returns a safe `500` detail (`"Failed to generate follow-up emails. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/{id}/outreach/recompare` now returns a safe `500` detail (`"Failed to refresh comparison. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/{id}/outreach/auto-send` now returns a safe `500` detail (`"Failed to send queued outreach emails. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/{id}/outreach/auto-start` now returns a safe `500` detail (`"Failed to start auto-outreach. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/{id}/outreach/check-inbox` now returns a safe `500` detail (`"Failed to check inbox. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/projects/{id}/phone/call` now returns a safe `500` detail (`"Failed to start phone call. Please try again."`) for unexpected failures, while preserving actionable `400` validation details.
- `POST /api/v1/projects/{id}/phone/calls/{call_id}/parse` now returns a safe `500` detail (`"Failed to parse call transcript. Please try again."`) for unexpected failures, without exposing internal exception strings.
- `POST /api/v1/dashboard/projects/start` normalizes `source` to supported dashboard entries (`dashboard_new`, `dashboard_search`) before telemetry/redirect attribution; unknown values default to `dashboard_new`.
- `POST /api/v1/projects/{id}/retrospective` is allowed only after the project is `complete`; otherwise the API returns `400` with `Retrospective can only be submitted for completed projects`.
- `POST /api/v1/projects/{id}/retrospective` accepts only the first submission per project; subsequent submissions return `409` with `Retrospective has already been submitted for this project.` and preserve the original feedback.
- `POST /api/v1/projects/{id}/cancel` and `POST /api/v1/projects/{id}/restart` now treat legacy records with blank `status` by falling back to canonical `current_stage`, so active runs can still be canceled and active-stage restarts are still blocked.
- Comparison stage now auto-converts unrealistically low per-unit international freight estimates for heavy/industrial products to `Freight quote required`, appending rationale in weaknesses and analysis narrative.

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
