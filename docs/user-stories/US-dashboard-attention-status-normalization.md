As a procurement manager
I want dashboard attention cards to normalize legacy status values
So that clarifying-required work is always visible even when old records have inconsistent status formatting

## Acceptance Criteria

1. Given a project with `status` stored as ` Clarifying ` and two `clarifying_questions`, when I call `GET /api/v1/dashboard/summary`, then the `attention` list includes one `clarifying_required` item for that project.
2. Given a project with blank `status`, `current_stage` set to ` Clarifying `, and one `clarifying_questions` entry, when I call `GET /api/v1/dashboard/summary`, then the `attention` list includes one `clarifying_required` item for that project.
3. Given a project with `status` stored as ` complete ` and non-empty `clarifying_questions`, when I call `GET /api/v1/dashboard/summary`, then no `clarifying_required` item is returned for that project.
