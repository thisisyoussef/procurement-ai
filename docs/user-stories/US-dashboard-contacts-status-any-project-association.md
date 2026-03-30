# User Story: Dashboard Contacts Status Filter Uses Any Associated Project

As a procurement manager
I want dashboard contacts status filters to match suppliers by any associated project
So that I do not lose relevant suppliers just because their latest interaction was in a different status

## Acceptance Criteria

1. Given a supplier linked to both a `discovering` project and a `complete` project, when I request `GET /api/v1/dashboard/contacts?status=discovering`, then that supplier is included even if `last_project_id` points to the `complete` project.
2. Given a supplier linked only to projects outside the selected statuses, when I request `GET /api/v1/dashboard/contacts?status=discovering`, then that supplier is excluded.
3. Given a legacy supplier row with no multi-project association metadata but `last_project_id` in a selected status, when I request `GET /api/v1/dashboard/contacts?status=discovering`, then that supplier remains included.
