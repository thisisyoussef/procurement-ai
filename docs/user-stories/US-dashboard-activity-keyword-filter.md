## User Story: Dashboard Activity Keyword Filter

As a procurement manager monitoring recent updates
I want to filter dashboard activity with a keyword query
So that I can quickly find relevant supplier and project events without scanning the full feed

## Acceptance Criteria

### Case 1: Keyword filter matches event content (case-insensitive)
Given I have dashboard activity events with mixed supplier names and descriptions
When I request `GET /api/v1/dashboard/activity?q=acme`
Then only events whose title, description, event type, or project name include `acme` are returned.

### Case 2: Whitespace-only query is treated as no filter
Given I have dashboard activity events
When I request `GET /api/v1/dashboard/activity?q=%20%20%20`
Then the API returns the same unfiltered event feed ordering as the default endpoint.

### Case 3: Overlong query input is rejected
Given I am authenticated
When I request `GET /api/v1/dashboard/activity?q=<121-character-string>`
Then the API returns `422 Unprocessable Entity`.
