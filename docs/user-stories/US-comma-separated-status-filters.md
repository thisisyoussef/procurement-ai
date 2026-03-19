## User Story: Comma-Separated Status Filters for Project Views

As a signed-in procurement manager
I want status filters to accept comma-separated values
So that shared links and bookmarked views keep multi-status filtering in one query parameter

## Acceptance Criteria

### Case 1: Project list supports comma-separated statuses
Given I own projects in `complete`, `failed`, and `discovering`
When I request `GET /api/v1/projects?status=complete,failed`
Then the response includes only `complete` and `failed` projects.

### Case 2: Dashboard summary supports comma-separated aliases
Given I own projects in `steering`, `complete`, and `canceled`
When I request `GET /api/v1/dashboard/summary?status=active,closed`
Then the response includes all active and terminal statuses represented by those aliases.

### Case 3: Comma-separated validation remains strict
Given I am authenticated
When I request `GET /api/v1/projects?status=parsing,not-real`
Then the API returns `422` and names `not-real` as invalid.
