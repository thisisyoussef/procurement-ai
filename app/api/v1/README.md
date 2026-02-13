# API v1 (`app/api/v1/`)

## Route Modules
- `projects.py`: project lifecycle, status, clarifications.
- `chat.py`: conversational actions and streaming.
- `outreach.py`: outreach planning/sending/parsing/status.
- `intake.py`, `leads.py`, `events.py`: growth funnel endpoints.
- `auth.py`: authentication/session endpoints.
- `phone.py`: phone escalation endpoints.
- `webhooks.py`: external webhook callbacks.
- `router.py`: route registration.

## Behavior-Preserving Cleanup Priorities
1. Reduce duplicated helper logic across route files.
2. Standardize HTTP error mapping and payload consistency.
3. Keep route function signatures stable for frontend compatibility.
