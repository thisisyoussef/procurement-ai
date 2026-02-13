# Repositories (`app/repositories/`)

## Purpose
Database persistence and query logic isolated from route handlers.

## Current Modules
- `runtime_repository.py`: runtime projects, leads, analytics events.
- `supplier_repository.py`: supplier memory and interaction history.
- `user_repository.py`: user account persistence.

## Cleanup Guidance
- Keep repositories pure persistence (no HTTP/state orchestration).
- Use normalized UUID and payload conversion helpers consistently.
- Favor explicit query helpers over ad-hoc JSON traversal in routes.
