## User Story: Safe Project Start Errors

As a signed-in procurement manager
I want project start failures to return a safe, consistent error message
So that I get clear retry guidance without exposing internal system details

## Acceptance Criteria

### Case 1: Product flow start error is sanitized
Given I am authenticated and project creation hits an unexpected server exception
When I call `POST /api/v1/projects`
Then the API returns `500` with `detail = "Failed to start project. Please try again."`
And the response does not include exception strings or tracebacks.

### Case 2: Dashboard quick-start error is sanitized
Given I am authenticated and dashboard project creation hits an unexpected server exception
When I call `POST /api/v1/dashboard/projects/start`
Then the API returns `500` with `detail = "Failed to start project. Please try again."`
And the response does not include exception strings or tracebacks.

### Case 3: Store-unavailable contract remains explicit
Given I am authenticated and the project store is unavailable
When I call `POST /api/v1/dashboard/projects/start`
Then the API returns `503` with the existing `Project store unavailable: ...` detail format.
