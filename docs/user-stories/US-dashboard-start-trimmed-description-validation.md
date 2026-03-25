## User Story: Dashboard Start Rejects Blank Briefs

As a signed-in procurement manager
I want dashboard quick-start descriptions to be validated after trimming whitespace
So that I cannot accidentally launch sourcing runs with empty or too-short briefs

## Acceptance Criteria

### Case 1: Whitespace-only description is rejected
Given I am authenticated on the dashboard
When I call `POST /api/v1/dashboard/projects/start` with a description containing only spaces
Then the API returns `422`
And no project is created.

### Case 2: Padded short description is rejected
Given I am authenticated on the dashboard
When I call `POST /api/v1/dashboard/projects/start` with a description like `"   short   "`
Then the API returns `422`
And no project is created.

### Case 3: Valid padded description is trimmed and persisted
Given I am authenticated on the dashboard
When I call `POST /api/v1/dashboard/projects/start` with a valid description surrounded by whitespace
Then the API returns `200` and starts the project
And the stored `product_description` and pipeline input use the trimmed description.
