# User Story: Dashboard Activity Project Name Enrichment

As a procurement manager
I want each dashboard activity event to show the related project name
So that I can quickly understand which project needs attention

## Acceptance Criteria

1. Given dashboard summary is filtered to a subset of project statuses, when recent activity includes an event from a different project, then that event still includes `project_name`.
2. Given dashboard activity events are loaded from DB-backed project events, when an event has a `project_id`, then the API response enriches that event with `project_name` from the user's project metadata.
3. Given dashboard activity pagination is requested, when events are returned with enriched names, then cursor behavior remains unchanged (`next_cursor` equals the last event timestamp in the page).
