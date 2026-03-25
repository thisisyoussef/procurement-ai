## User Story: Project Search Matches Project ID

As a signed-in procurement manager
I want project search to match project IDs in addition to title and description
So that I can quickly reopen a known run from an ID shared in updates or support threads

## Acceptance Criteria

### Case 1: Project list matches project ID keywords
Given I own a project with ID `proj-abc-1234`
When I request `GET /api/v1/projects?q=ABC-1234`
Then the response includes that project using case-insensitive ID matching.

### Case 2: Dashboard summary matches project ID keywords
Given I own a dashboard project with ID `proj-dash-abc-1010`
When I request `GET /api/v1/dashboard/summary?q=ABC-1010`
Then the dashboard cards include that project using case-insensitive ID matching.

### Case 3: Status and project ID filters intersect
Given I own two projects whose IDs both include `3333`, one `discovering` and one `complete`
When I request `GET /api/v1/projects?status=discovering&q=3333` or `GET /api/v1/dashboard/summary?status=discovering&q=3333`
Then only the `discovering` project is returned.
