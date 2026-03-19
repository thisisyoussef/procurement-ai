# US: Query Length Guardrails for Project Search

As a procurement manager
I want project search query inputs to enforce a safe maximum length
So that dashboard and project list searches stay responsive and reliable

## Acceptance Criteria

### Scenario 1: Project list rejects overlong query
Given I am authenticated
When I request `GET /api/v1/projects?q=<121-character-string>`
Then the API responds with `422 Unprocessable Entity`

### Scenario 2: Dashboard summary rejects overlong query
Given I am authenticated
When I request `GET /api/v1/dashboard/summary?q=<121-character-string>`
Then the API responds with `422 Unprocessable Entity`

### Scenario 3: Valid queries continue to work
Given I am authenticated
When I request either endpoint with a query at or below 120 characters
Then the API applies the existing case-insensitive title filtering behavior
