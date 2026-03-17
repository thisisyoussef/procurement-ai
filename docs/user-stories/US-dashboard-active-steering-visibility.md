## User Story: Dashboard Active Filter Includes Steering

As a procurement manager
I want steering-stage projects to appear when I select the Active filter on the dashboard
So that I can quickly resume projects waiting on checkpoint steering decisions

## Acceptance Criteria

### Case 1: Active alias includes steering work
Given I own one project in `steering` and one in `complete`
When I request `GET /api/v1/dashboard/summary?status=active`
Then only the `steering` project is returned in the dashboard project cards.

### Case 2: Steering can be filtered explicitly
Given I own one project in `steering` and one in `complete`
When I request `GET /api/v1/dashboard/summary?status=steering`
Then only the `steering` project is returned.

### Case 3: Dashboard UI Active preset includes steering status
Given I am viewing `/dashboard` with the Active preset selected
When the frontend builds status filters for summary polling
Then the request includes `status=steering` with the other in-progress statuses.
