# User Story: Safe Retrospective Submission Errors

As a procurement manager
I want retrospective submission failures to return safe, non-sensitive error messages
So that I can retry confidently without exposing internal system details.

## Acceptance Criteria

1. Given a completed project where retrospective submission hits an unexpected internal failure,
When I call `POST /api/v1/projects/{project_id}/retrospective`,
Then the API returns `500` with detail `"Failed to submit retrospective. Please try again."` and does not include internal exception text.

2. Given a non-completed project,
When I call `POST /api/v1/projects/{project_id}/retrospective`,
Then the API returns `400` with detail `"Retrospective can only be submitted for completed projects"`.

3. Given a completed project that already has retrospective feedback,
When I call `POST /api/v1/projects/{project_id}/retrospective` again,
Then the API returns `409` with detail `"Retrospective has already been submitted for this project."` and preserves the original retrospective.
