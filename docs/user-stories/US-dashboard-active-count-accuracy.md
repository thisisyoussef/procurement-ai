## User Story: Dashboard Active Count Accuracy

As an authenticated procurement manager
I want the dashboard greeting active-project count to include all in-progress runs
So that I can trust the workload summary before opening project cards.

## Acceptance Criteria

### Case 1: Steering projects are counted as active
Given I own one project in `steering` and one in `complete`
When I request `GET /api/v1/dashboard/summary`
Then `greeting.active_projects` is `1`.

### Case 2: Active count normalizes status formatting
Given I own a project with status value ` Parsing `
When I request `GET /api/v1/dashboard/summary`
Then `greeting.active_projects` treats it as an active project and returns `1`.

### Case 3: Terminal statuses are excluded
Given I own projects in `failed`, `canceled`, and `complete`
When I request `GET /api/v1/dashboard/summary`
Then `greeting.active_projects` is `0`.
