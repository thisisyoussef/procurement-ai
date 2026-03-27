# US: Safe Error Responses for Outreach Follow-Up Generation

As a procurement manager
I want follow-up generation failures to return a safe generic error message
So that internal system details are not exposed in user-facing API responses

## Acceptance Criteria

### Scenario 1: Unexpected follow-up generation failures are safely masked
Given I am authenticated and outreach has started for my project
When `POST /api/v1/projects/{id}/outreach/follow-up` raises an unexpected internal exception
Then the API responds with `500`
And the error detail is exactly `"Failed to generate follow-up emails. Please try again."`

### Scenario 2: Sensitive exception text is never leaked to clients
Given an unexpected follow-up generation exception includes sensitive internal content
When I call `POST /api/v1/projects/{id}/outreach/follow-up`
Then the response detail does not include any raw exception text

### Scenario 3: Existing HTTP errors are preserved
Given follow-up generation flow raises an `HTTPException` (for example `503` project store unavailable)
When I call `POST /api/v1/projects/{id}/outreach/follow-up`
Then the API returns the original HTTP status code and detail unchanged
