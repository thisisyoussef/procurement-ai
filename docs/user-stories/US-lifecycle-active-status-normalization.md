# User Story: Lifecycle actions honor canonical active status

As a procurement user managing live sourcing runs  
I want cancel/restart actions to treat legacy-formatted project state as active when appropriate  
So that I cannot accidentally restart a run that is already in progress and I can still cancel active stage-only records.

## Acceptance Criteria (Given/When/Then)

1. Given a project with legacy-formatted active status (`" Discovering "`)  
   When I call `POST /api/v1/projects/{id}/restart`  
   Then the API returns `409` with `"Project is currently running. Cancel the run before restarting."`.

2. Given a project with blank `status` but active `current_stage` (`"verifying"`)  
   When I call `POST /api/v1/projects/{id}/restart`  
   Then the API returns `409` with the same running-project guardrail message.

3. Given a project with blank `status` but active `current_stage` (`"discovering"`)  
   When I call `POST /api/v1/projects/{id}/cancel`  
   Then the API cancels the run and returns `200` with `status` set to `"canceled"`.
