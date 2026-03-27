As a procurement manager reviewing supplier outreach
I want to filter dashboard contacts by project status
So that I can focus on suppliers tied to active work or closed outcomes.

Acceptance criteria

Given I am authenticated
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then only contacts from projects in the `discovering` status are returned.

Given I am authenticated
When I request `GET /api/v1/dashboard/contacts?status=closed,parsing`
Then contacts are filtered using expanded statuses (`complete`, `failed`, `canceled`, `parsing`).

Given I am authenticated
When I request `GET /api/v1/dashboard/contacts?status=unknown`
Then the API responds with `422 Unprocessable Entity` and an invalid status detail.
