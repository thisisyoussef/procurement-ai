## User Story: Retrospective Submission Only After Completion

As a procurement manager  
I want to submit retrospective feedback only after a project is complete  
So that historical feedback reflects finished sourcing outcomes

### Acceptance Criteria

1. Given a project in a non-terminal active stage (for example `discovering`), when I submit `POST /api/v1/projects/{project_id}/retrospective`, then the API returns `400` with `Retrospective can only be submitted for completed projects` and does not persist retrospective data.
2. Given a completed project that I own, when I submit `POST /api/v1/projects/{project_id}/retrospective`, then the API returns `200` with `status=recorded` and the retrospective is visible in `GET /api/v1/projects/{project_id}/status`.
3. Given a completed project owned by another user, when I submit `POST /api/v1/projects/{project_id}/retrospective`, then the API returns `403 Forbidden` and does not persist retrospective data.
