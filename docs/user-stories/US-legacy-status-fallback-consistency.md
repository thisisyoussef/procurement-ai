As a procurement manager
I want project list and dashboard status handling to fall back to stage when legacy status is blank
So that active work never disappears from my filters or active-project counts

## Acceptance Criteria

1. Given a legacy project with blank `status` and `current_stage` set to `discovering`, when I call `GET /api/v1/projects?status=discovering`, then the project is returned with canonical `"status": "discovering"` and `"current_stage": "discovering"`.
2. Given a legacy project with blank `status` and `current_stage` set to `steering`, when I call `GET /api/v1/dashboard/summary?status=active`, then the project appears in the filtered dashboard cards with canonical `"status": "steering"`.
3. Given a legacy project with blank `status` and `current_stage` set to `parsing`, when I call `GET /api/v1/dashboard/summary`, then `greeting.active_projects` includes that project in the active count.
