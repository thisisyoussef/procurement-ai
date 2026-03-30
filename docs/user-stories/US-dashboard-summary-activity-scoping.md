As a procurement manager
I want dashboard summary activity to respect my project filters
So that the recent activity feed stays relevant to the projects I am viewing

Acceptance Criteria

1. Given I request `GET /api/v1/dashboard/summary?status=discovering`
When my account has both `discovering` and `complete` projects with activity
Then the response includes only `discovering` project cards and only activity events for those `discovering` projects.

2. Given I request `GET /api/v1/dashboard/summary?q=bottle`
When only one project title/description matches `bottle`
Then the response includes only the matching project card and activity events only for that matching project.

3. Given I request `GET /api/v1/dashboard/summary` with filters that match no projects
When no project IDs satisfy the combined filters
Then the response returns an empty `projects` array and an empty `recent_activity` array.
