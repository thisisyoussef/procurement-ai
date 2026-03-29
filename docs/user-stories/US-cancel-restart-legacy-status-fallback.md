# User Story: Cancel and Restart Honor Legacy Stage Fallback

As a procurement manager
I want cancel and restart controls to respect the project's active stage even when legacy records have blank status fields
So that I can safely stop active runs and avoid accidental restarts while a run is still in progress

## Acceptance Criteria

1. Given a project whose `status` is blank and `current_stage` is `discovering`, when I call `POST /api/v1/projects/{project_id}/cancel`, then the API returns `200` with `status: "canceled"` and persists `status/current_stage` as `canceled`.
2. Given a project whose `status` is blank and `current_stage` is `complete`, when I call `POST /api/v1/projects/{project_id}/cancel`, then the API returns `200` with `already_terminal: true` and `status: "complete"`.
3. Given a project whose `status` is blank and `current_stage` is an active stage (for example `verifying`), when I call `POST /api/v1/projects/{project_id}/restart`, then the API returns `409` with `Project is currently running. Cancel the run before restarting.`
