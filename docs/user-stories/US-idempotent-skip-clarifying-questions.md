# User Story: Idempotent Skip Clarifying Questions

As a sourcing manager
I want skipping clarifying questions to be retry-safe
So that accidental double-clicks or network retries do not block my project from continuing

## Acceptance Criteria

### Case 1: First skip resumes pipeline
Given my project is in `clarifying` with pending clarifying questions
When I call `POST /api/v1/projects/{project_id}/skip-questions`
Then the API returns `200` with `status` set to `resumed`
And the project moves to `discovering`
And clarifying questions are cleared

### Case 2: Retry skip is idempotent
Given my project is already in `discovering` and has no pending clarifying questions
When I call `POST /api/v1/projects/{project_id}/skip-questions` again
Then the API returns `200` with `status` set to `resumed`
And the response includes `already_skipped: true`
And no second resume task is scheduled

### Case 3: Non-clarifying invalid stages are still rejected
Given my project is in a non-clarifying stage that is not a completed skip transition (for example `complete`)
When I call `POST /api/v1/projects/{project_id}/skip-questions`
Then the API returns `400` with detail `Project is not waiting for answers`
