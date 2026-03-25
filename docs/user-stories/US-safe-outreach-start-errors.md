# US: Safe Error Responses for Outreach Start

As a procurement manager
I want outreach start failures to return a safe generic error message
So that internal system details are not exposed in user-facing API responses

## Acceptance Criteria

### Scenario 1: Unexpected outreach start failures are safely masked
Given I am authenticated and have a complete project
When `POST /api/v1/projects/{id}/outreach/start` raises an unexpected internal exception
Then the API responds with `500`
And the error detail is exactly `"Failed to start outreach. Please try again."`

### Scenario 2: Sensitive exception text is never leaked to clients
Given an unexpected outreach start exception includes sensitive internal content
When I call `POST /api/v1/projects/{id}/outreach/start`
Then the response detail does not include any raw exception text

### Scenario 3: User-correctable validation errors remain unchanged
Given I am authenticated and provide only invalid supplier indices
When I call `POST /api/v1/projects/{id}/outreach/start`
Then the API responds with `400`
And the error detail remains `"No valid supplier indices provided"`
