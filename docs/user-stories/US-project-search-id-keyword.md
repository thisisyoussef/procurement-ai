## User Story: Project Search Matches Project IDs

As a signed-in procurement manager
I want project keyword search to match project IDs in addition to title and description
So that I can quickly find projects from copied IDs and shared links

## Acceptance Criteria

### Case 1: Project list matches project ID keyword
Given I own a project with ID `proj-2026-gearbox` and a different project with ID `proj-2026-labels`
When I request `GET /api/v1/projects?q=GEARBOX`
Then the response includes only `proj-2026-gearbox` using case-insensitive ID matching.

### Case 2: Dashboard summary matches project ID keyword
Given I own dashboard projects with IDs `proj-dash-gearbox` and `proj-dash-labels`
When I request `GET /api/v1/dashboard/summary?q=GEARBOX`
Then the dashboard `projects` list includes only `proj-dash-gearbox`.

### Case 3: Status and ID keyword filters intersect
Given I own two projects with IDs containing `gearbox`, one `discovering` and one `complete`
When I request `GET /api/v1/projects?status=discovering&q=gearbox` or `GET /api/v1/dashboard/summary?status=discovering&q=gearbox`
Then only the `discovering` project is returned.
