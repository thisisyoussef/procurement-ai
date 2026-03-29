## User Story: Dashboard Clarifying Attention Reliability

As an authenticated procurement manager
I want dashboard attention cards to recognize clarifying projects even with legacy status formatting
So that I never miss required clarification steps needed to keep sourcing moving.

## Acceptance Criteria

### Case 1: Clarifying attention normalizes legacy status formatting
Given I own a project with `status` value ` Clarifying `
When I request `GET /api/v1/dashboard/summary`
Then the response includes a `clarifying_required` attention item for that project.

### Case 2: Clarifying attention falls back to stage when status is blank
Given I own a project where `status` is blank and `current_stage` is ` Clarifying `
When I request `GET /api/v1/dashboard/summary`
Then the response includes a `clarifying_required` attention item for that project.

### Case 3: Non-clarifying statuses do not create clarifying attention
Given I own a project with normalized status `complete`
When I request `GET /api/v1/dashboard/summary`
Then the response does not include a `clarifying_required` attention item for that project.
