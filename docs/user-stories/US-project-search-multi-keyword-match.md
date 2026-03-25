## User Story: Project Search Supports Multi-Keyword Matching

As a signed-in procurement manager
I want project search to match multiple keywords across title and requirement text
So that I can quickly find the right case even when I only remember partial details

## Acceptance Criteria

### Case 1: Project list matches multiple keywords in any order
Given I own a project titled `Precision Motor Housing` with description `Need zinc-coated steel fasteners for assembly line.`
When I request `GET /api/v1/projects?q=assembly%20motor`
Then the project is returned even though one keyword comes from description and the other from title.

### Case 2: Dashboard summary supports the same multi-keyword behavior
Given I own a dashboard project titled `Precision motor housings` with description `Need zinc-coated steel fasteners for assembly line.`
When I request `GET /api/v1/dashboard/summary?q=assembly%20motor`
Then that project card is returned.

### Case 3: Search requires all keywords
Given I own a project titled `Precision Motor Housing` with description `Need zinc-coated steel fasteners for assembly line.`
When I request `GET /api/v1/projects?q=motor%20titanium`
Then the project is not returned because `titanium` is missing.
