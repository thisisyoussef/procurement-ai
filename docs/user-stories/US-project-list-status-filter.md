# User Story: Project List Status Filter

As a signed-in procurement manager
I want to filter my project list by pipeline status
So that I can focus on in-flight work or closed outcomes without scanning all projects.

## Acceptance Criteria

### Case 1: Single status filter
Given I own projects across `parsing`, `discovering`, and `complete` statuses
When I request `GET /api/v1/projects?status=parsing`
Then the response contains only my projects with `status = parsing`.

### Case 2: Multiple status filters
Given I own projects in `complete`, `failed`, and `discovering`
When I request `GET /api/v1/projects?status=complete&status=failed`
Then the response includes only `complete` and `failed` projects, still ordered by existing recency rules.

### Case 3: Invalid status value
Given I am authenticated
When I request `GET /api/v1/projects?status=not-real`
Then the API returns `422` with a clear validation message listing allowed statuses.
