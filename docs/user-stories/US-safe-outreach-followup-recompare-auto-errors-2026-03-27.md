As a procurement manager
I want outreach automation endpoints to return safe generic failures
So that internal exception details are never exposed in API responses.

Acceptance Criteria
1. Given an unexpected runtime failure in follow-up generation
When `POST /api/v1/projects/{project_id}/outreach/follow-up` is called
Then the API returns `500` with `Failed to generate follow-up emails. Please try again.`

2. Given an unexpected runtime failure during quote re-compare
When `POST /api/v1/projects/{project_id}/outreach/recompare` is called
Then the API returns `500` with `Failed to refresh comparison. Please try again.`

3. Given an unexpected runtime failure during auto-start outreach
When `POST /api/v1/projects/{project_id}/outreach/auto-start` is called
Then the API returns `500` with `Failed to start auto outreach. Please try again.`

4. Given an unexpected runtime failure while checking inbox replies
When `POST /api/v1/projects/{project_id}/outreach/check-inbox` is called
Then the API returns `500` with `Failed to check inbox. Please try again.`
