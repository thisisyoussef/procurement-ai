As a procurement manager reviewing supplier outreach
I want dashboard contact status filters to match any linked project for each supplier
So that suppliers are not hidden when their latest interaction belongs to a different status.

Acceptance criteria

Given I am authenticated and a supplier is linked to both `discovering` and `complete` projects
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then that supplier is returned even if `last_project_id` points to the `complete` project.

Given I am authenticated and a legacy supplier row only has `last_project_id`
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then the supplier is still matched by `last_project_id` for backward compatibility.

Given I am authenticated and a supplier is linked only to non-requested statuses
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then that supplier is excluded from the response.
