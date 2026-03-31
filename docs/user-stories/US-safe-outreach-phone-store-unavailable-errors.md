# US: Safe Store-Unavailable Errors for Outreach and Phone APIs

As a procurement manager
I want outreach and phone endpoints to return safe generic 503 errors when project storage is unavailable
So that backend exception details are not exposed to users

## Acceptance Criteria

### Scenario 1: Outreach start masks store outage internals
Given project storage is unavailable while loading project data
When I call `POST /api/v1/projects/{id}/outreach/start`
Then the API responds with `503`
And the error detail is exactly `"Outreach service is temporarily unavailable. Please try again."`
And raw exception text is never included

### Scenario 2: Phone call start masks store outage internals
Given project storage is unavailable while loading project data
When I call `POST /api/v1/projects/{id}/phone/call`
Then the API responds with `503`
And the error detail is exactly `"Phone service is temporarily unavailable. Please try again."`
And raw exception text is never included

### Scenario 3: Phone configure masks save-path outages
Given project loading succeeds but storage fails while saving updated phone config
When I call `POST /api/v1/projects/{id}/phone/configure`
Then the API responds with `503`
And the error detail is exactly `"Phone service is temporarily unavailable. Please try again."`
And raw exception text is never included
