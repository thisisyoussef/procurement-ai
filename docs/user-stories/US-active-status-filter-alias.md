## User Story: Active Status Filter Alias

As an authenticated procurement manager
I want to request project lists with `status=active`
So that I can quickly view only in-progress work without enumerating every pipeline stage.

## Acceptance Criteria

### Case 1: Project list active alias
Given I own projects in `steering` and `complete`
When I request `GET /api/v1/projects?status=active`
Then the response includes only in-progress projects and excludes `complete`.

### Case 2: Dashboard summary active alias
Given I own projects in `steering` and `complete`
When I request `GET /api/v1/dashboard/summary?status=active`
Then project cards include only in-progress statuses and keep `steering` visible.

### Case 3: Invalid status validation remains strict
Given I am authenticated
When I request either endpoint with `status=not-real`
Then the API returns `422` with a clear validation message that still lists valid status values (including alias `active`).
