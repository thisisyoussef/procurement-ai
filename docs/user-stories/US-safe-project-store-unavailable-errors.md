## User Story: Safe Project Store Unavailable Errors

As a signed-in procurement manager
I want project endpoints to return a consistent safe message when storage is unavailable
So that I can retry confidently without seeing internal backend details

## Acceptance Criteria

### Case 1: Product flow project start store outage is sanitized
Given I am authenticated and the project store is unavailable during `POST /api/v1/projects`
When the API responds
Then it returns `503` with `detail = "Project service is temporarily unavailable. Please try again."`
And the response does not include internal exception strings.

### Case 2: Project status store outage is sanitized
Given I am authenticated and the project store is unavailable during `GET /api/v1/projects/{project_id}/status`
When the API responds
Then it returns `503` with `detail = "Project service is temporarily unavailable. Please try again."`
And the response does not include internal exception strings.

### Case 3: Project list store outage is sanitized
Given I am authenticated and the project store is unavailable during `GET /api/v1/projects`
When the API responds
Then it returns `503` with `detail = "Project service is temporarily unavailable. Please try again."`
And the response does not include internal exception strings.
