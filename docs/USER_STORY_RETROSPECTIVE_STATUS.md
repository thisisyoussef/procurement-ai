# User Story: Retrospective Visibility After Refresh

As a procurement manager
I want my submitted retrospective feedback to appear in project status
So that I can confirm feedback was saved and avoid duplicate submissions

## Acceptance Criteria

1. Given a completed project with no retrospective, when I fetch `GET /api/v1/projects/{project_id}/status`, then the response includes `"retrospective": null`.
2. Given I submit retrospective feedback through `POST /api/v1/projects/{project_id}/retrospective`, when I fetch project status, then the same retrospective payload is returned in `"retrospective"`.
3. Given a project owned by another user, when I fetch that project status, then the API returns `403 Forbidden` and does not expose retrospective data.
