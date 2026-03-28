As a procurement manager
I want retrospective submission failures to return a safe, generic error
So that internal system details are never exposed to users

Acceptance Criteria
1. Given a completed project with no prior retrospective
When the user submits `POST /api/v1/projects/{project_id}/retrospective` and an unexpected persistence error occurs
Then the API responds with `500` and detail `Failed to submit retrospective. Please try again.` and does not include internal exception text.

2. Given a completed project that already has retrospective feedback
When the user submits `POST /api/v1/projects/{project_id}/retrospective` again
Then the API responds with `409` and detail `Retrospective has already been submitted for this project.`

3. Given a completed project with no prior retrospective
When the user submits valid retrospective feedback successfully
Then the API responds with `200` and `{"status":"recorded"}`, and `GET /api/v1/projects/{project_id}/status` returns that saved retrospective payload.
