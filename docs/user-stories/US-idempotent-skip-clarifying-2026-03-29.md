# User Story — Idempotent Clarification Skip

As a sourcing manager
I want the "skip clarifying questions" action to be safe to retry
So that accidental duplicate submits do not block my project from continuing

## Acceptance Criteria

1. Given a project in `clarifying`
When I call `POST /api/v1/projects/{id}/skip-questions`
Then the API returns `200` with `status: resumed`, clears pending clarifying questions, and moves the project to `discovering`.

2. Given a project where clarifications were already skipped and it is already in `discovering`
When I call `POST /api/v1/projects/{id}/skip-questions` again
Then the API returns `200` with `status: resumed` and does not re-trigger another pipeline resume task.

3. Given a project in a stage other than `clarifying` or already-skipped `discovering`
When I call `POST /api/v1/projects/{id}/skip-questions`
Then the API returns `400` with `Project is not waiting for answers`.
