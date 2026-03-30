# User Story: Dashboard Summary Recent Activity Filter Scoping

As a procurement manager
I want dashboard summary recent activity to respect my project filters
So that the activity feed stays aligned with the projects I am reviewing

## Acceptance Criteria

1. Given dashboard projects in both active and complete statuses, when I call `GET /api/v1/dashboard/summary?status=discovering`, then `recent_activity` includes only events tied to discovering projects.
2. Given dashboard projects with different keywords, when I call `GET /api/v1/dashboard/summary?q=bottle`, then `recent_activity` includes only events from projects matching the `bottle` query.
3. Given no projects match the status/query filters, when I call `GET /api/v1/dashboard/summary` with those filters, then the response returns an empty `projects` list and an empty `recent_activity` list.
