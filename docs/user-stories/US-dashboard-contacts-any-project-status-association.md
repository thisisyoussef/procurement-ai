# User Story: Dashboard Contacts Status Scope Uses Any Associated Project

## Story
As a founder reviewing supplier contacts
I want status filters to include suppliers tied to any project in that status
So that I don't lose relevant suppliers just because their most recent interaction came from another project stage

## Acceptance Criteria
1. Given a supplier has interactions in both an active and a closed project
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then the supplier appears in results even if `last_project_id` points to a closed project

2. Given a supplier has interactions only in closed projects
When I request `GET /api/v1/dashboard/contacts?status=discovering`
Then the supplier is excluded from results

3. Given no valid active-project association can be found for a supplier
When a status filter is applied
Then filtering still uses `last_project_id` as a safe fallback and returns only matching contacts
