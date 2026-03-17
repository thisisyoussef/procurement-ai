## User Story: Canonical Project Status In List Response

As a signed-in procurement manager
I want each project in the list API to return canonical status and stage values
So that workspace badges and phase indicators remain reliable for legacy data

## Acceptance Criteria

### Case 1: Legacy status/current_stage are normalized in response
Given I own a project with stored `status` and `current_stage` set to ` Parsing `
When I request `GET /api/v1/projects`
Then that project is returned with `status=parsing` and `current_stage=parsing`.

### Case 2: Missing or blank current_stage falls back to status
Given I own a project with stored `status` of ` Discovering ` and blank `current_stage`
When I request `GET /api/v1/projects`
Then that project is returned with `status=discovering` and `current_stage=discovering`.

### Case 3: Existing canonical values remain unchanged
Given I own a project with stored `status=complete` and `current_stage=complete`
When I request `GET /api/v1/projects`
Then that project is returned with `status=complete` and `current_stage=complete`.
