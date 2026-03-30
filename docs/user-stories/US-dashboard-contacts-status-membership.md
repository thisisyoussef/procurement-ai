# US: Dashboard Contacts Status Membership

As a procurement manager
I want dashboard contact status filters to include suppliers tied to any matching project
So that I do not lose relevant suppliers just because their latest interaction was in a different status

## Acceptance Criteria

### Scenario 1: Include supplier with at least one matching-status project
Given a supplier has interactions across both `discovering` and `complete` projects
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then the supplier appears in results because they are linked to a `discovering` project

### Scenario 2: Exclude supplier without matching-status projects
Given a supplier is linked only to `complete` projects
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then the supplier is excluded from results

### Scenario 3: Empty results when no projects match status filter
Given I have no projects in `discovering` status
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then the API returns an empty supplier list with `count` equal to `0`
