# Data Models (`app/models/`)

## Purpose
SQLAlchemy ORM models for runtime project state, users, and supplier memory.

## Model Groups
- Runtime/Growth: `runtime.py`
- Supplier memory/history: `supplier.py`
- User/auth identity: `user.py`
- Legacy project model surface: `project.py`

## Cleanup Guidance
- Keep model names and columns aligned with migration history.
- Use additive migrations for schema changes.
- Document cross-table assumptions in corresponding repositories.
