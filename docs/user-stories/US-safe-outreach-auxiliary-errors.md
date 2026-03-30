# User Story: Safe Outreach Auxiliary Error Responses

As a procurement operator
I want outreach auxiliary endpoints to return safe generic failures on unexpected errors
So that internal system details are not exposed in API responses

## Acceptance Criteria

### Scenario 1: Follow-up generation masks unexpected failures
Given a valid project with outreach started
When `POST /api/v1/projects/{id}/outreach/follow-up` hits an unexpected internal exception
Then the API returns `500` with `"Failed to generate follow-up emails. Please try again."`
And the response does not include raw internal exception text

### Scenario 2: Recompare preserves validation errors
Given a project where all parsed quotes are excluded
When `POST /api/v1/projects/{id}/outreach/recompare` is called
Then the API returns `400` with `"All quoted suppliers are excluded"`
And the request is not converted into a generic `500`

### Scenario 3: Auto-send masks unexpected failures
Given a project with at least one queued auto-send draft
When `POST /api/v1/projects/{id}/outreach/auto-send` hits an unexpected internal exception
Then the API returns `500` with `"Failed to auto-send outreach emails. Please try again."`
And the response does not expose provider/internal error strings

### Scenario 4: Inbox checks mask unexpected failures
Given a valid project with outreach started
When `POST /api/v1/projects/{id}/outreach/check-inbox` hits an unexpected internal exception
Then the API returns `500` with `"Failed to check inbox. Please try again."`
And the response does not include raw internal exception details
