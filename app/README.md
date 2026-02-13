# Backend (`app/`)

## Purpose
FastAPI backend that orchestrates procurement pipeline stages, supplier memory, outreach operations, and integrations.

## Layering Rules
- `api/` handles HTTP transport concerns and request/response mapping.
- `services/` orchestrates domain workflows and store abstractions.
- `repositories/` handles SQLAlchemy persistence details.
- `agents/` encapsulates LLM/provider-driven decision logic.
- `schemas/` defines canonical contracts used across modules.
- `core/` hosts shared infrastructure (config, auth, DB, scheduler, logging).

## Safety Rules for Cleanup
- Keep route paths and response shapes backward-compatible.
- Avoid introducing direct repo access from API routers.
- Prefer additive internal refactors with regression tests.
