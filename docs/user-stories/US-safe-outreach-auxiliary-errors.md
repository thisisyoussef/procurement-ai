# US: Safe Error Responses for Auxiliary Outreach Endpoints

As a procurement manager
I want follow-up, recompare, auto-start, and inbox-check failures to return safe generic errors
So that internal system details are not exposed in user-facing API responses

## Acceptance Criteria

### Scenario 1: Follow-up generation failures are safely masked
Given I am authenticated and outreach has started for my project
When `POST /api/v1/projects/{id}/outreach/follow-up` raises an unexpected internal exception
Then the API responds with `500`
And the error detail is exactly `"Failed to generate follow-up emails. Please try again."`

### Scenario 2: Recompare failures are safely masked while validation remains actionable
Given I am authenticated and outreach has started for my project
When `POST /api/v1/projects/{id}/outreach/recompare` raises an unexpected internal exception
Then the API responds with `500`
And the error detail is exactly `"Failed to re-compare supplier quotes. Please try again."`

Given there are no parsed quotes yet
When I call `POST /api/v1/projects/{id}/outreach/recompare`
Then the API responds with `400`
And the error detail remains `"No parsed quotes to compare"`

### Scenario 3: Auto-start and inbox-check failures are safely masked
Given I am authenticated and auto-outreach/inbox checks are configured for my project
When `POST /api/v1/projects/{id}/outreach/auto-start` or `POST /api/v1/projects/{id}/outreach/check-inbox` raises an unexpected internal exception
Then the API responds with `500`
And the error details are exactly:
- `"Failed to start auto outreach. Please try again."`
- `"Failed to check inbox. Please try again."`
And raw exception text is never included in responses
