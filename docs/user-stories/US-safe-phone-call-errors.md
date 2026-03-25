# User Story: Safe Phone Outreach Error Responses

As a procurement manager  
I want phone outreach endpoints to return safe, consistent failure messages for unexpected backend errors  
So that internal system details are not exposed while I still get actionable validation feedback.

## Acceptance Criteria

1. Given a project ready for phone outreach and an unexpected internal failure occurs while starting a supplier call  
When I `POST /api/v1/projects/{project_id}/phone/call`  
Then the API returns `500` with detail `Failed to start phone call. Please try again.` and does not include raw exception text.

2. Given a project with a completed call transcript and an unexpected internal failure occurs during call transcript parsing  
When I `POST /api/v1/projects/{project_id}/phone/calls/{call_id}/parse`  
Then the API returns `500` with detail `Failed to parse call transcript. Please try again.` and does not include raw exception text.

3. Given a phone call start request fails input validation inside the call initiation flow (for example invalid destination number)  
When I `POST /api/v1/projects/{project_id}/phone/call`  
Then the API preserves a `400` response with the original actionable validation detail.
