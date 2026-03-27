# US: Safe Error Responses for Outreach Automation Operations

As a procurement operator
I want outreach automation endpoints to return safe and consistent error responses
So that internal exception details are never exposed and clients can handle failures predictably

## Acceptance Criteria

### Scenario 1: Follow-up draft generation hides unexpected internal failures
Given I am authenticated and outreach has started for my project
When `POST /api/v1/projects/{id}/outreach/follow-up` raises an unexpected internal exception
Then the API responds with `500`
And the error detail is exactly `"Failed to generate follow-up drafts. Please try again."`

### Scenario 2: Recompare keeps user-correctable validation errors
Given all parsed quotes for a project are already excluded
When I call `POST /api/v1/projects/{id}/outreach/recompare`
Then the API responds with `400`
And the error detail remains `"All quoted suppliers are excluded"`

### Scenario 3: Inbox and auto-start failures are safely masked
Given I am authenticated and outreach automation is configured
When `POST /api/v1/projects/{id}/outreach/auto-start` or `POST /api/v1/projects/{id}/outreach/check-inbox` raises an unexpected internal exception
Then each API responds with `500`
And each response contains only its fixed safe failure detail without raw exception text
