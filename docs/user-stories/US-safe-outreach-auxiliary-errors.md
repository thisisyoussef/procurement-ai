As a procurement manager
I want outreach auxiliary endpoints to return safe, consistent errors
So that internal exception details are never exposed and validation behavior stays predictable.

Acceptance Criteria

1. Given I am authenticated and `POST /api/v1/projects/{id}/outreach/follow-up` hits an unexpected internal exception, when the request fails, then the API returns `500` with `detail = "Failed to generate follow-up emails. Please try again."` and does not include raw exception text.
2. Given I am authenticated and `POST /api/v1/projects/{id}/outreach/recompare` has parsed quotes where every quote is excluded, when I request recompare, then the API preserves `400` with `detail = "All quoted suppliers are excluded"` instead of converting it to `500`.
3. Given I am authenticated and either `POST /api/v1/projects/{id}/outreach/auto-send` or `POST /api/v1/projects/{id}/outreach/check-inbox` hits an unexpected internal exception, when the request fails, then each endpoint returns `500` with a safe fixed detail message and no raw exception text.
