# User Story: Safe Project Store Unavailable Errors

As a signed-in procurement manager
I want project endpoints to return a safe, consistent message when the project store is unavailable
So that I know to retry without seeing internal infrastructure details

## Acceptance Criteria

### Case 1: Project creation store outage is sanitized
Given I am authenticated and the project store throws a connectivity error while creating a project
When I call `POST /api/v1/projects`
Then the API returns `503` with `detail = "Project service is temporarily unavailable. Please try again."`
And the response does not include internal hostnames, DSNs, or credentials.

### Case 2: Project list store outage is sanitized
Given I am authenticated and the project store is unavailable while listing projects
When I call `GET /api/v1/projects`
Then the API returns `503` with `detail = "Project service is temporarily unavailable. Please try again."`
And the response does not include internal exception text.

### Case 3: Project status store outage is sanitized
Given I am authenticated and the project store is unavailable while loading a project status
When I call `GET /api/v1/projects/{project_id}/status`
Then the API returns `503` with `detail = "Project service is temporarily unavailable. Please try again."`
And the response does not include raw store error details.
