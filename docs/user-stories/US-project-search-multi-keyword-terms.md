## User Story: Project Search Supports Multi-Keyword Matching

As a signed-in procurement manager
I want project search to require all query terms across project id, title, and description
So that I can find the exact run quickly when I only remember partial words.

## Acceptance Criteria

### Case 1: Project list matches when all terms are present
Given I own a project with title `Biodegradable Capsules` and description `Need coffee-compatible capsule supplier.`
When I request `GET /api/v1/projects?q=coffee%20capsule`
Then the response includes that project because both terms match across its searchable fields.

### Case 2: Dashboard summary excludes partial matches
Given I own one project matching both terms (`coffee` and `capsule`) and another matching only `coffee`
When I request `GET /api/v1/dashboard/summary?q=coffee%20capsule`
Then only the project matching all terms is returned in dashboard cards.

### Case 3: Multi-keyword query intersects with status filters
Given I own a `discovering` project and a `complete` project that both include `zinc` and `fasteners`
When I request `GET /api/v1/projects?status=discovering&q=zinc%20fasteners` or `GET /api/v1/dashboard/summary?status=discovering&q=zinc%20fasteners`
Then only the `discovering` project is returned.
