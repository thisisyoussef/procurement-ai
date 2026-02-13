# Migrations (`alembic/`)

## Purpose
Database schema evolution for runtime projects, growth data, supplier memory/history, and auth.

## Workflow
1. Create additive revision under `alembic/versions/`.
2. Keep upgrade/downgrade deterministic.
3. Run migrations in staging before production rollout.

## Cleanup Guidance
- Do not rewrite applied migration history.
- Avoid migration side effects that alter runtime semantics unexpectedly.
- Keep model/repository assumptions aligned with migration schema.
