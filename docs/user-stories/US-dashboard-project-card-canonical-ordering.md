## User Story: Dashboard Project Cards Canonical and Prioritized

As an authenticated procurement manager
I want dashboard project cards to return canonical status values and prioritize active work
So that I can trust card badges and focus first on projects that need action

## Acceptance Criteria

### Case 1: Dashboard cards canonicalize legacy status values
Given I own a project stored with `status` and `current_stage` as ` Complete `
When I request `GET /api/v1/dashboard/summary`
Then the returned project card has `status=complete` and `phase_label=Order placed`.

### Case 2: Active projects are shown before terminal projects
Given I own active and complete projects
When I request `GET /api/v1/dashboard/summary`
Then active project cards appear before complete/failed/canceled cards even if terminal projects were updated more recently.

### Case 3: Cards use created_at fallback when updated_at is missing
Given I own active projects without `updated_at` timestamps
When I request `GET /api/v1/dashboard/summary`
Then active cards are ordered by newest `created_at` first.
