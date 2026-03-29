As a procurement manager
I want to archive completed or failed projects
So that my default project list stays focused on active or currently relevant work

### Case 1: Archive a terminal project
Given I own a project in `complete` status
When I call `POST /api/v1/projects/{project_id}/archive` with an optional reason
Then the API returns `200` with `status=archived` and stores `archived_at` metadata.

### Case 2: Prevent archiving active work
Given I own a project in `discovering` status
When I call `POST /api/v1/projects/{project_id}/archive`
Then the API returns `409` with `Only terminal projects can be archived.`.

### Case 3: Default list hides archived projects unless requested
Given I own one archived project and one non-archived project
When I call `GET /api/v1/projects`
Then only the non-archived project is returned by default.
When I call `GET /api/v1/projects?include_archived=true`
Then both projects are returned.
