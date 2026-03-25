## User Story: Project List Title Keyword Search

As a signed-in procurement manager
I want to filter my project list by title keyword
So that I can quickly find the right project when managing many sourcing runs

## Acceptance Criteria

### Case 1: Keyword filter returns matching titles
Given I own projects titled `Biodegradable Coffee Capsules` and `Luxury Candle Labels`
When I request `GET /api/v1/projects?q=coffee`
Then the response includes only `Biodegradable Coffee Capsules`.

### Case 2: Keyword filtering is case-insensitive
Given I own a project titled `Precision Motor Shafts`
When I request `GET /api/v1/projects?q=SHAFTS`
Then the response includes that project.

### Case 3: Whitespace-only keyword is ignored
Given I own at least one project
When I request `GET /api/v1/projects?q=   `
Then the API behaves like the default list endpoint and does not apply keyword filtering.
