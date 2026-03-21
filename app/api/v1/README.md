# API v1 (`app/api/v1/`)

## Route Modules
- `projects.py`: project lifecycle, status, clarifications.
- `chat.py`: conversational actions and streaming.
- `outreach.py`: outreach planning/sending/parsing/status.
- `intake.py`, `leads.py`, `events.py`: growth funnel endpoints.
- `auth.py`: authentication/session endpoints.
- `phone.py`: phone escalation endpoints.
- `webhooks.py`: external webhook callbacks.
- `router.py`: route registration.

## Behavior-Preserving Cleanup Priorities
1. Reduce duplicated helper logic across route files.
2. Standardize HTTP error mapping and payload consistency.
3. Keep route function signatures stable for frontend compatibility.

## User-Visible API Behavior
- `GET /api/v1/projects` now returns authenticated projects ordered for actionability:
  - Active pipeline runs first (`parsing`, `clarifying`, `discovering`, `verifying`, `steering`, `comparing`, `recommending`, `outreaching`)
  - Then by most recent `updated_at`
  - Then by `created_at` when needed as fallback
- `GET /api/v1/projects` now returns canonical lowercase, trimmed `status` and `current_stage` values in each list item (legacy stored formatting is normalized in the response).
- `GET /api/v1/projects` accepts optional repeated `status` query parameters
  (example: `?status=parsing&status=discovering`) and returns only matching statuses.
- `GET /api/v1/projects` normalizes stored project status values (trim + lowercase) when
  filtering and ordering active work, so legacy values such as ` Parsing ` still behave as active.
- `GET /api/v1/projects` and `GET /api/v1/dashboard/summary` also accept `status=active` as
  an alias for all in-progress pipeline statuses (`parsing` through `outreaching`, including `steering`).
- `GET /api/v1/projects` accepts optional `q` for case-insensitive project title keyword filtering
  (example: `?q=coffee`), applied after ownership and optional status filtering.
  The `q` value is limited to 120 characters.
- `GET /api/v1/dashboard/summary` greeting counts `steering` as active work and normalizes
  status formatting (trim + lowercase) before active count aggregation.
- `GET /api/v1/dashboard/summary` project cards now normalize legacy status/current stage
  values before rendering (`" Complete "` -> `complete`) so badge and phase UI stay consistent.
- `GET /api/v1/dashboard/summary` project cards are ordered for actionability:
  active projects first, then by most recent `updated_at`, then `created_at` fallback.
- `GET /api/v1/dashboard/summary` accepts optional `q` for case-insensitive dashboard
  project-title keyword filtering (example: `?q=coffee`), combinable with optional `status` filters.
  The `q` value is limited to 120 characters.
- Project list items include optional `created_at` and `updated_at` timestamps.
- `GET /api/v1/projects/{project_id}/status` now includes `retrospective` when post-run feedback has already been submitted (otherwise `null`).
- `POST /api/v1/projects` trims surrounding whitespace for `title` and `product_description`, and rejects whitespace-only values.
- `POST /api/v1/projects` and `POST /api/v1/dashboard/projects/start` now return a safe, fixed `500` message (`Failed to start project. Please try again.`) for unexpected start failures, without exposing internal exception details.
- `POST /api/v1/dashboard/projects/start` is the dashboard quick-start entrypoint:
  - Accepts dashboard source context and normalizes to supported values (`dashboard_search`, `dashboard_new`)
  - Unknown or malformed `source` values default to `dashboard_new`
  - Returns `redirect_path` so clients can route with preserved attribution (`entry=<source>`)
