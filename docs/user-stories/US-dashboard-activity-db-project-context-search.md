# User Story: Dashboard Activity DB Project Context Search

As a procurement manager
I want dashboard activity keyword search to match project context fields for DB-backed events
So that I can quickly find relevant events by project name or ID even when timeline fallback is not used

## Acceptance Criteria

1. Given dashboard activity events loaded from the DB where the event payload does not include the query token, when I request `GET /api/v1/dashboard/activity?q=<project-name-fragment>`, then events for projects whose names include the fragment are returned.
2. Given dashboard activity events loaded from the DB where title/description/event type do not include the query token, when I request `GET /api/v1/dashboard/activity?q=<project-id-fragment>`, then events with matching `project_id` are returned.
3. Given I request `GET /api/v1/dashboard/activity?status=discovering&q=<project-name-fragment>`, when only discovering projects match the status filter, then only events from those project IDs are returned.
