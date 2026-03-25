As a procurement manager
I want the project status endpoint to return canonical stage/status values
So that dashboard and workspace views stay consistent for legacy projects after refresh

## Acceptance Criteria

1. Given a project with legacy formatted values (`" Complete "` / `" ReCommending "`), when I call `GET /api/v1/projects/{project_id}/status`, then the response returns `"status": "complete"` and `"current_stage": "recommending"`.
2. Given a project with missing/blank `status` and a valid stage (`" Verifying "`), when I call `GET /api/v1/projects/{project_id}/status`, then the response returns `"status": "verifying"` and `"current_stage": "verifying"`.
3. Given a project with missing/blank `current_stage` and a valid status (`" Discovering "`), when I call `GET /api/v1/projects/{project_id}/status`, then the response returns `"status": "discovering"` and `"current_stage": "discovering"`.
