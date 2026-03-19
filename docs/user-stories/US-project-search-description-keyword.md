## User Story: Project Search Matches Requirement Text

As a signed-in procurement manager
I want project keyword search to match both project title and requirement description
So that I can find projects even when I only remember what we needed sourced

## Acceptance Criteria

### Case 1: Project list matches description keywords
Given I own a project titled `Run A` with product description `Need zinc-coated steel fasteners for assembly line.`
When I request `GET /api/v1/projects?q=fasteners`
Then the response includes that project even though the title does not contain `fasteners`.

### Case 2: Dashboard summary matches description keywords
Given I own a dashboard project titled `Run A` with product description `Need zinc-coated steel fasteners for assembly line.`
When I request `GET /api/v1/dashboard/summary?q=FASTENERS`
Then the dashboard cards include that project using case-insensitive keyword matching.

### Case 3: Status and description keyword filters intersect
Given I own two projects that both mention `fasteners` in description, one `discovering` and one `complete`
When I request `GET /api/v1/projects?status=discovering&q=fasteners` or `GET /api/v1/dashboard/summary?status=discovering&q=fasteners`
Then only the `discovering` project is returned.
