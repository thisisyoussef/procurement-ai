# API Layer (`app/api/`)

## Purpose
HTTP-facing route modules and API router composition.

## Structure
- `v1/`: versioned endpoints.
- Each route module should focus on transport, auth gating, and service orchestration calls.

## Refactor Rules
- Preserve existing endpoint paths and request/response contracts.
- Keep ownership checks and authorization in route layer.
- Move reusable business logic into `services/` when it grows.
