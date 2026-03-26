# US: Safe Error Responses for Outreach Quote Parsing

As a procurement manager
I want outreach quote parsing failures to return a safe generic error message
So that internal system details are not exposed in user-facing API responses

## Acceptance Criteria

### Scenario 1: Unexpected parse failures are safely masked
Given I am authenticated and outreach has started for my project
When `POST /api/v1/projects/{id}/outreach/parse-response` raises an unexpected internal exception
Then the API responds with `500`
And the error detail is exactly `"Failed to parse supplier response. Please try again."`

### Scenario 2: Sensitive exception text is never leaked to clients
Given an unexpected parse exception includes sensitive internal content
When I call `POST /api/v1/projects/{id}/outreach/parse-response`
Then the response detail does not include any raw exception text

### Scenario 3: User-correctable validation errors remain unchanged
Given I am authenticated and provide an out-of-range `supplier_index`
When I call `POST /api/v1/projects/{id}/outreach/parse-response`
Then the API responds with `400`
And the error detail remains `"Invalid supplier index"`
