# Core Infrastructure (`app/core/`)

## Purpose
Shared infrastructure utilities used across backend layers.

## Modules
- `config.py`: settings and environment loading.
- `database.py`: SQLAlchemy engine/session setup.
- `auth.py`: token/session auth helpers.
- `scheduler.py`: background periodic outreach workers.
- `email_service.py`, `phone_service.py`: provider wrappers.
- `progress.py`, `log_stream.py`: pipeline progress/log streaming.
- `llm_gateway.py`: model invocation boundary.

## Cleanup Guidance
- Keep integration points explicit and auditable.
- Prefer typed return payloads and explicit failure states.
- Avoid cross-import cycles from core into API modules.
