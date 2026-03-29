# User Story: Dashboard Safe Store-Unavailable Errors

As a procurement manager  
I want dashboard endpoints to return a safe, consistent unavailable message when project storage is down  
So that I get clear guidance without seeing internal infrastructure details

## Acceptance Criteria

1. Given dashboard summary data depends on the project store and the store is unavailable, when I request `GET /api/v1/dashboard/summary`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.` and does not include backend exception text.
2. Given dashboard activity data depends on the project store and the store is unavailable, when I request `GET /api/v1/dashboard/activity`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.` and does not include backend exception text.
3. Given dashboard contacts data depends on the project store and the store is unavailable, when I request `GET /api/v1/dashboard/contacts`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.` and does not include backend exception text.
4. Given dashboard project start depends on the project store and the store is unavailable, when I request `POST /api/v1/dashboard/projects/start`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.` and does not include backend exception text.
