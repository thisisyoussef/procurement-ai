## User Story: Dashboard Project Status Filters

As a signed-in procurement manager
I want to filter dashboard project cards by status
So that I can focus on active work or failed outcomes without scanning every project.

## Acceptance Criteria

### Case 1: Active preset filter
Given I own projects across `parsing`, `discovering`, and `complete` statuses
When I open the dashboard and select the `Active` filter
Then only project cards in active pipeline statuses are shown.

### Case 2: Failed preset filter
Given I own projects in `failed`, `complete`, and `discovering`
When I select the `Failed` filter
Then only cards with `status = failed` remain in the project grid.

### Case 3: API status validation
Given I am authenticated
When I request `GET /api/v1/dashboard/summary?status=not-real`
Then the API returns `422` with a clear message listing allowed status values.
