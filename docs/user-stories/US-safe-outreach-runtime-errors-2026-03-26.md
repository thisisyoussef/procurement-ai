# User Story: Safe Runtime Error Responses for Outreach Operations

As a procurement manager
I want outreach operations to return safe generic errors on unexpected failures
So that internal exception details are not exposed in API responses

## Acceptance Criteria

### Scenario 1: Follow-up generation failures are safely masked
Given I am authenticated and outreach has started for my project
When `POST /api/v1/projects/{id}/outreach/follow-up` hits an unexpected internal exception
Then the API responds with `500`
And the detail is exactly `"Failed to generate follow-up emails. Please try again."`

### Scenario 2: Recompare failures are safely masked
Given I am authenticated and my project has parsed supplier quotes
When `POST /api/v1/projects/{id}/outreach/recompare` hits an unexpected internal exception
Then the API responds with `500`
And the detail is exactly `"Failed to refresh comparison with parsed quotes. Please try again."`

### Scenario 3: Auto-outreach start failures are safely masked
Given I am authenticated and auto-outreach is configured for my project
When `POST /api/v1/projects/{id}/outreach/auto-start` hits an unexpected internal exception
Then the API responds with `500`
And the detail is exactly `"Failed to start auto outreach. Please try again."`

### Scenario 4: Inbox check failures are safely masked
Given I am authenticated and outreach is active for my project
When `POST /api/v1/projects/{id}/outreach/check-inbox` hits an unexpected internal exception
Then the API responds with `500`
And the detail is exactly `"Failed to check inbox for supplier responses. Please try again."`
