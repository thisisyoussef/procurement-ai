# User Story: Dashboard Summary Status-Scoped Activity

As a procurement manager
I want dashboard summary activity to follow the selected project status filter
So that the activity feed stays relevant to the projects I am currently reviewing

## Acceptance Criteria

1. Given I have `discovering` and `complete` projects with recent timeline events, when I request `GET /api/v1/dashboard/summary?status=discovering`, then `recent_activity` only includes events from `discovering` projects.
2. Given I have both active and terminal projects with events, when I request `GET /api/v1/dashboard/summary?status=closed`, then `recent_activity` only includes events from terminal (`complete`, `failed`, `canceled`) projects.
3. Given none of my projects match the requested status filter, when I request `GET /api/v1/dashboard/summary?status=complete`, then both `projects` and `recent_activity` are empty arrays.
