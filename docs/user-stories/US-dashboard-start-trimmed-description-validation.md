## User Story: Dashboard Quick-Start Description Validation

As a procurement manager starting a project from the dashboard
I want quick-start descriptions to be trimmed and validated for meaningful content
So that empty or low-signal requests do not start broken sourcing runs

## Acceptance Criteria

### Case 1: Whitespace-only description is rejected
Given I am authenticated on the dashboard
When I call `POST /api/v1/dashboard/projects/start` with `description` containing only whitespace
Then the API returns `422`
And no project is created.

### Case 2: Description too short after trimming is rejected
Given I am authenticated on the dashboard
When I call `POST /api/v1/dashboard/projects/start` with a description that becomes fewer than 10 characters after trimming
Then the API returns `422`
And no project is created.

### Case 3: Valid description is trimmed before persistence
Given I am authenticated on the dashboard
When I call `POST /api/v1/dashboard/projects/start` with leading/trailing spaces around a valid description
Then the API creates the project successfully
And stores `product_description` without leading/trailing whitespace.
