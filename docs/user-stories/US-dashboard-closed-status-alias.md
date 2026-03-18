## User Story: Closed Status Alias for Project Filtering

As a signed-in procurement manager
I want to filter projects with a single `closed` status alias
So that I can quickly review completed, failed, and canceled runs without selecting each status separately

## Acceptance Criteria

### Case 1: Project list closed alias
Given I own projects in `complete`, `failed`, `canceled`, and `discovering`
When I request `GET /api/v1/projects?status=closed`
Then the response includes only `complete`, `failed`, and `canceled` projects.

### Case 2: Dashboard summary closed alias
Given I own projects in `complete`, `failed`, `canceled`, and `discovering`
When I request `GET /api/v1/dashboard/summary?status=closed`
Then dashboard project cards include only terminal projects.

### Case 3: Validation messaging includes closed alias
Given I am authenticated
When I request `GET /api/v1/projects?status=not-real` or `GET /api/v1/dashboard/summary?status=not-real`
Then the API returns `422` and the allowed-values message lists both aliases: `active` and `closed`.
