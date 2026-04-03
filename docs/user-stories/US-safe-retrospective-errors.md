# User Story: Safe Retrospective Submission Errors

As a procurement manager
I want retrospective submission failures to return a safe, retryable error message
So that I can retry confidently without seeing internal system details

## Acceptance Criteria

1. Given a completed project owned by me, when an unexpected error happens while saving retrospective feedback, then `POST /api/v1/projects/{project_id}/retrospective` returns `500` with detail `Failed to record retrospective. Please try again.`
2. Given an unexpected retrospective submission failure, when I inspect the API error detail, then it does not include the raw internal exception text.
3. Given a project that is not complete or already has retrospective feedback, when I submit retrospective feedback, then the endpoint still returns the existing business-rule responses (`400` for not complete, `409` for duplicate) unchanged.
