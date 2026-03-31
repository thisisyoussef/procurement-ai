# User Story: Safe Dashboard Store-Unavailable Errors

As a sourcing founder using the dashboard  
I want dashboard endpoints to return safe outage messages when project storage is unavailable  
So that I get clear retry guidance without exposing internal infrastructure details.

## Acceptance Criteria

### 1) Summary endpoint masks backend outage details
Given the project store is unavailable for `/api/v1/dashboard/summary`  
When I request dashboard summary data  
Then the API returns `503` with `Project data is temporarily unavailable. Please try again.`  
And the response does not include raw backend exception text.

### 2) Activity and contacts endpoints use the same safe outage contract
Given the project store is unavailable for `/api/v1/dashboard/activity` or `/api/v1/dashboard/contacts`  
When I request activity or contacts data  
Then each API returns `503` with `Project data is temporarily unavailable. Please try again.`  
And no internal outage details are leaked in the response.

### 3) Dashboard quick-start preserves the same safe outage contract
Given the project store is unavailable for `/api/v1/dashboard/projects/start`  
When I submit a valid dashboard quick-start request  
Then the API returns `503` with `Project data is temporarily unavailable. Please try again.`  
And the response excludes backend exception details.
