# Services (`app/services/`)

## Purpose
Business-layer orchestration and abstraction around storage/memory.

## Modules
- `project_store.py`: database/in-memory store abstraction and fallback policy.
- `supplier_memory.py`: memory read/write helpers and interaction logging.

## Cleanup Guidance
- Services should mediate domain operations, not transport details.
- Keep store fallback behavior explicit and environment-aware.
- Ensure service methods expose clear mutation semantics.
