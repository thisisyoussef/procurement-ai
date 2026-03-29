As a procurement manager reviewing supplier outreach
I want contacts status filtering to include suppliers tied to any matching project
So that I do not miss relevant suppliers just because their latest interaction happened on a closed project.

Acceptance criteria

Given I am authenticated and a supplier is linked to both discovering and complete projects
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then that supplier is included even if its `last_project_id` belongs to a complete project.

Given I am authenticated and a supplier is linked only to complete projects
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then that supplier is excluded from the response.

Given I am authenticated and a supplier's `last_project_id` is in discovering
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then that supplier remains included as before.
