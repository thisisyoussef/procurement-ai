As a procurement manager
I want dashboard attention prompts to normalize legacy project status values
So that I can always see clarifying-required actions on older projects

## Acceptance Criteria

1. Given a project with status value `" Clarifying "`, when I call `GET /api/v1/dashboard/summary`, then the response includes a `clarifying_required` attention item for that project.
2. Given a project with blank `status` and `current_stage` set to `"Clarifying"`, when I call `GET /api/v1/dashboard/summary`, then the response includes a `clarifying_required` attention item for that project.
3. Given a project with status `"complete"` (even if stale `clarifying_questions` data exists), when I call `GET /api/v1/dashboard/summary`, then no `clarifying_required` attention item is returned.
