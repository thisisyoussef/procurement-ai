# User Story: Archive Finished Projects from Default List

## Story
As a procurement coordinator
I want to archive projects that are no longer active
So that my default project list stays focused on current work

## Acceptance Criteria
1. Given I own a project in a non-active status (`complete`, `failed`, or `canceled`)
When I call `POST /api/v1/projects/{project_id}/archive`
Then the API returns `200` with `{ "project_id": "...", "status": "archived" }`
And the project is stored with `status=archived` and `current_stage=archived`.

2. Given I do not own a project
When I call `POST /api/v1/projects/{project_id}/archive`
Then the API returns `403 Forbidden`
And the project remains unchanged.

3. Given I have both active and archived projects
When I call `GET /api/v1/projects` without a `status` filter
Then archived projects are excluded from the response.

4. Given I have archived projects
When I call `GET /api/v1/projects?status=archived`
Then archived projects are returned.

5. Given I own a currently active project (`parsing`, `discovering`, etc.)
When I call `POST /api/v1/projects/{project_id}/archive`
Then the API returns `409`
And the response detail is `Active projects cannot be archived. Cancel or complete the run first.`
