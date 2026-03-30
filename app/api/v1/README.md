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
- `GET /api/v1/projects` treats blank legacy `status` as the canonical `current_stage` value
  for filtering, active-first sorting, and response payloads, so stage-only records remain visible.
- `GET /api/v1/projects` accepts optional repeated `status` query parameters
  (example: `?status=parsing&status=discovering`) and returns only matching statuses.
- `GET /api/v1/projects` normalizes stored project status values (trim + lowercase) when
  filtering and ordering active work, so legacy values such as ` Parsing ` still behave as active.
- `GET /api/v1/projects` and `GET /api/v1/dashboard/summary` also accept `status=active` as
  an alias for all in-progress pipeline statuses (`parsing` through `outreaching`, including `steering`).
- `GET /api/v1/projects` accepts optional `q` for case-insensitive project title keyword filtering
  (example: `?q=coffee`), applied after ownership and optional status filtering.
  Multi-term queries require all terms to match in the title/description text (order-insensitive),
  for example `?q=motor aluminum`.
  The `q` value is limited to 120 characters.
- `GET /api/v1/dashboard/summary` greeting counts `steering` as active work and normalizes
  status formatting (trim + lowercase) before active count aggregation.
- `GET /api/v1/dashboard/summary` treats blank legacy `status` as the canonical `current_stage`
  value for status filtering and greeting active-count calculations.
- `GET /api/v1/dashboard/summary` project cards now normalize legacy status/current stage
  values before rendering (`" Complete "` -> `complete`) so badge and phase UI stay consistent.
- `GET /api/v1/dashboard/summary` project cards are ordered for actionability:
  active projects first, then by most recent `updated_at`, then `created_at` fallback.
- `GET /api/v1/dashboard/summary` accepts optional `q` for case-insensitive dashboard
  project-title keyword filtering (example: `?q=coffee`), combinable with optional `status` filters.
  Multi-term queries require all terms to match in title/description text (order-insensitive),
  for example `?q=motor aluminum`.
  The `q` value is limited to 120 characters.
- `GET /api/v1/dashboard/contacts` accepts optional `q` for case-insensitive supplier contact
  keyword filtering across name, email, phone, website, city, and country. The `q` value is
  limited to 120 characters. Phone matching also supports digit-only queries against formatted
  phone values (example: `3125550142` matches `+1 (312) 555-0142`). Query filtering is applied
  before response limiting so relevant matches are preserved.
- `GET /api/v1/dashboard/contacts` merges DB-backed contact rows with runtime project discovery
  contacts (deduplicated by supplier identity), so newly discovered suppliers remain visible even
  before interaction rows are persisted. If DB access fails, runtime contacts are used as fallback.
- `GET /api/v1/dashboard/activity` falls back to in-memory per-project timeline events
  (newest first) when DB-backed dashboard activity rows are unavailable, and keeps
  cursor pagination behavior (`cursor` returns older events only, `next_cursor` is the
  last event timestamp returned).
- Project list items include optional `created_at` and `updated_at` timestamps.
- `GET /api/v1/projects/{project_id}/status` now includes `retrospective` when post-run feedback has already been submitted (otherwise `null`).
- `GET /api/v1/projects/{project_id}/status` now returns canonical lowercase, trimmed `status` and `current_stage`; if either field is blank in legacy records, it falls back to the other canonical value so clients always receive a consistent stage/status pair.
- `POST /api/v1/projects/{project_id}/retrospective` is accepted only when project status is `complete`; non-complete projects receive `400` with `Retrospective can only be submitted for completed projects`.
- `POST /api/v1/projects` trims surrounding whitespace for `title` and `product_description`, and rejects whitespace-only values.
- `POST /api/v1/projects` and `POST /api/v1/dashboard/projects/start` now return a safe, fixed `500` message (`Failed to start project. Please try again.`) for unexpected start failures, without exposing internal exception details.
- `POST /api/v1/projects/{project_id}/outreach/start` now returns a safe, fixed `500` message (`Failed to start outreach. Please try again.`) for unexpected failures, without exposing internal exception details.
- `POST /api/v1/projects/{project_id}/outreach/parse-response` now returns a safe, fixed `500` message (`Failed to parse supplier response. Please try again.`) for unexpected failures, without exposing internal exception details.
- `POST /api/v1/projects/{project_id}/phone/call` now returns a safe, fixed `500` message (`Failed to start phone call. Please try again.`) for unexpected failures, while preserving actionable `400` validation details.
- `POST /api/v1/projects/{project_id}/phone/calls/{call_id}/parse` now returns a safe, fixed `500` message (`Failed to parse call transcript. Please try again.`) for unexpected failures, without exposing internal exception details.
- `POST /api/v1/dashboard/projects/start` is the dashboard quick-start entrypoint:
  - Accepts dashboard source context and normalizes to supported values (`dashboard_search`, `dashboard_new`)
  - Unknown or malformed `source` values default to `dashboard_new`
  - Returns `redirect_path` so clients can route with preserved attribution (`entry=<source>`)
