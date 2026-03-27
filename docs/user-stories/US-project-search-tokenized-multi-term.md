## User Story: Multi-Term Project Search

As a signed-in procurement manager
I want project search to match multiple keywords across title and requirement text
So that I can find the right sourcing run even when I remember only partial terms

## Acceptance Criteria

### Case 1: Multi-term query matches across title + description
Given I own a project whose title includes `Bottle` and description includes `steel`
When I request `GET /api/v1/projects?q=steel bottle` or `GET /api/v1/dashboard/summary?q=steel bottle`
Then that project is returned even though the terms are split across different fields.

### Case 2: Query parsing ignores punctuation and extra spaces
Given I own a project containing `precision` and `shafts`
When I request `GET /api/v1/projects?q=  precision,   shafts!! ` or `GET /api/v1/dashboard/summary?q=  precision,   shafts!! `
Then the project is returned because punctuation and spacing noise are ignored.

### Case 3: All query tokens are required
Given I own a project that matches `labels` but not `steel`
When I request `GET /api/v1/projects?q=labels steel` or `GET /api/v1/dashboard/summary?q=labels steel`
Then that project is not returned because every token must match.
