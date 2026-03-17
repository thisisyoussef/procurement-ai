## User Story: Project List Status Normalization

As a signed-in procurement manager
I want project list status filtering and sorting to normalize legacy status formatting
So that active and status-filtered views remain accurate even when stored status values include whitespace or mixed case

## Acceptance Criteria

### Case 1: Single status filter normalizes stored status
Given I own a project with stored status ` Parsing `
When I request `GET /api/v1/projects?status=parsing`
Then the response includes that project.

### Case 2: Active alias includes normalized active statuses
Given I own a project with stored status ` Parsing ` and another in `complete`
When I request `GET /api/v1/projects?status=active`
Then the response includes only the in-progress project.

### Case 3: Default list ordering treats normalized active statuses as active
Given I own a project with stored status ` Parsing ` and another newer `complete` project
When I request `GET /api/v1/projects`
Then the normalized active project appears before the complete project.
