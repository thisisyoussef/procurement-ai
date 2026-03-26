As a sourcing manager
I want quick search failures to return a safe, consistent error message
So that I can retry confidently without seeing internal system details

## Acceptance Criteria

1. Given an authenticated user and a valid quick-search request, when `POST /api/v1/projects/search` succeeds, then the API responds `200` with pipeline summary fields (`status`, `error`, `parsed_requirements`, `discovery_results`, `verification_results`, `comparison_result`, `recommendation`).
2. Given an authenticated user and an unexpected internal failure while running quick search, when the user calls `POST /api/v1/projects/search`, then the API responds `500` with detail `Failed to run quick search. Please try again.`.
3. Given an unauthenticated caller, when they call `POST /api/v1/projects/search`, then the API responds `401 Unauthorized`.
