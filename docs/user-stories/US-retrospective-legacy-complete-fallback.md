As a procurement manager
I want retrospective completion checks to use canonical status fallback for legacy records
So that completed legacy projects can still capture post-project feedback

## Acceptance Criteria

1. Given a project with blank `status` and `current_stage` set to `complete`, when I submit `POST /api/v1/projects/{project_id}/retrospective`, then the API returns `200` with `status=recorded` and persists the retrospective.
2. Given a project with blank `status` and `current_stage` set to `discovering`, when I submit `POST /api/v1/projects/{project_id}/retrospective`, then the API returns `400` with `Retrospective can only be submitted for completed projects` and does not persist retrospective data.
3. Given a project with blank `status`, `current_stage` set to `complete`, and an existing retrospective, when I submit `POST /api/v1/projects/{project_id}/retrospective`, then the API returns `409` with `Retrospective has already been submitted for this project.` and preserves the original feedback.
