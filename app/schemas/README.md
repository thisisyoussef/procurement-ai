# Schemas (`app/schemas/`)

## Purpose
Pydantic contracts shared by agents, API handlers, and frontend integration points.

## Files
- `agent_state.py`: pipeline and outreach state contracts.
- `project.py`: request/response API schemas.
- `auth.py`: authentication payloads.
- `supplier.py`: supplier-facing contract models.

## Cleanup Guidance
- Treat schema changes as contract changes; update frontend and tests together.
- Prefer additive fields and backward-compatible defaults.
- Keep enum/state names stable unless versioned migration is planned.
