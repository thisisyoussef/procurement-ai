# User Story: Safe Outreach Runtime Errors

As a procurement manager
I want outreach endpoints to return safe, non-sensitive error messages on unexpected failures
So that I can retry confidently without exposing internal system details.

## Acceptance Criteria

1. Given an outreach response parsing request where parsing throws an unexpected runtime error,
When I call `POST /api/v1/projects/{id}/outreach/parse-response`,
Then the API returns `500` with detail `"Failed to parse outreach response. Please try again."` and does not include internal exception text.

2. Given a follow-up generation request where follow-up drafting throws an unexpected runtime error,
When I call `POST /api/v1/projects/{id}/outreach/follow-up`,
Then the API returns `500` with detail `"Failed to generate follow-up emails. Please try again."` and does not include internal exception text.

3. Given an inbox check request where inbox polling throws an unexpected runtime error,
When I call `POST /api/v1/projects/{id}/outreach/check-inbox`,
Then the API returns `500` with detail `"Failed to check inbox. Please try again."` and does not include internal exception text.

4. Given a recompare or auto-outreach start request where backend processing throws an unexpected runtime error,
When I call `POST /api/v1/projects/{id}/outreach/recompare` or `POST /api/v1/projects/{id}/outreach/auto-start`,
Then each endpoint returns `500` with a safe, endpoint-specific retry message and does not include internal exception text.
