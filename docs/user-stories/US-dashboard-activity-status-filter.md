# User Story: Dashboard Activity Status Filter

As a procurement manager
I want to filter dashboard activity by project status
So that I can focus on updates from active or closed work without noise

## Acceptance Criteria

1. Given I have activity from projects in multiple statuses, when I call `GET /api/v1/dashboard/activity?status=discovering`, then the response includes only events from `discovering` projects.
2. Given I need terminal-work visibility, when I call `GET /api/v1/dashboard/activity?status=closed`, then the response includes events only from `complete`, `failed`, or `canceled` projects.
3. Given an unsupported status token, when I call `GET /api/v1/dashboard/activity?status=in_progress`, then the API returns `422` with an invalid-status validation message.
