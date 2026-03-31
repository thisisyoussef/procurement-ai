As a procurement manager
I want dashboard endpoints to return safe outage errors when project storage is down
So that I can understand the system is temporarily unavailable without seeing internal infrastructure details

## Acceptance Criteria

1. Given project storage is unavailable, when I call `GET /api/v1/dashboard/summary`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.`.
2. Given project storage is unavailable, when I call `GET /api/v1/dashboard/activity`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.`.
3. Given project storage is unavailable, when I call `GET /api/v1/dashboard/contacts`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.`.
4. Given project storage is unavailable, when I call `POST /api/v1/dashboard/projects/start`, then the API returns `503` with `Project data is temporarily unavailable. Please try again.` and does not include backend outage details.
