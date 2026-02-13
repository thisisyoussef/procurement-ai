# Tamkin Procurement AI

Tamkin is an AI-assisted sourcing platform for finding, vetting, comparing, and contacting suppliers.

## Repository Layout
- `app/`: FastAPI backend, agents, persistence, and orchestration.
- `frontend/`: Next.js product and landing experience.
- `alembic/`: Database migrations.
- `tests/`: API and agent tests.
- `docs/`: Engineering plans, cleanup roadmap, and architecture notes.

## Core Runtime Flow
1. User creates a project from landing or product UI.
2. Backend pipeline parses requirements, discovers suppliers, verifies, compares, and recommends.
3. Outreach stage drafts/sends supplier emails with approval controls.
4. Project status and supplier interactions are persisted for memory reuse.

## Local Development
- Backend: `uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Tests: `pytest`
- Frontend build: `cd frontend && npm run build`

## Documentation Index
- `docs/REFACTORING_PLAN.md`
- `docs/REFACTORING_TRACKER.md`
- Directory READMEs under `app/`, `frontend/src/`, `tests/`, and `alembic/`.
