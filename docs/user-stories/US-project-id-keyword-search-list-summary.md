# User Story: Project ID Keyword Search for List and Dashboard Summary

As a procurement operator
I want project keyword search to also match project IDs
So that I can quickly find a project from copied links or IDs without remembering title text

## Acceptance Criteria

### Case 1: Project list matches by project ID
Given I have projects with IDs `proj-abc-123` and `proj-def-456`
When I request `GET /api/v1/projects?q=ABC-123`
Then the response includes only `proj-abc-123`

### Case 2: Dashboard summary matches by project ID
Given I have dashboard projects with IDs `proj-dash-target-001` and `proj-dash-other-002`
When I request `GET /api/v1/dashboard/summary?q=TARGET-001`
Then the response includes only `proj-dash-target-001`

### Case 3: Status + project ID filters combine correctly
Given I have one `discovering` project and one `complete` project whose IDs both include `id-match`
When I request `GET /api/v1/dashboard/summary?status=discovering&q=id-match`
Then the response includes only the `discovering` project
