## User Story: Project Search Multi-Term Matching

As a signed-in procurement manager
I want project search to match multiple words regardless of order across title and description
So that I can find the right sourcing run using natural query fragments

## Acceptance Criteria

### Case 1: Project list matches multiple terms in any order
Given I own a project with description `Need zinc-coated steel fasteners for assembly line.`
When I request `GET /api/v1/projects?q=fasteners%20steel`
Then the response includes that project even though the terms are not adjacent in the same order.

### Case 2: Project list matches terms across title and description
Given I own a project titled `Run A Fasteners` with description `Need zinc-coated steel for assembly line.`
When I request `GET /api/v1/projects?q=run%20steel`
Then the response includes that project by combining matches across title and description.

### Case 3: Dashboard summary requires all query terms
Given I own a dashboard project that contains `labels` but not `steel` in title/description
When I request `GET /api/v1/dashboard/summary?q=labels%20steel`
Then that project is not included because every query term must match.
