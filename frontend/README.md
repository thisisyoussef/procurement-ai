# Frontend (`frontend/`)

## Purpose
Next.js application for Tamkin landing and product workspace.

## Top-Level Areas
- `src/app/`: route entries and global styling.
- `src/components/`: UI building blocks and workflow views.
- `src/contexts/`: shared state/context providers.
- `src/hooks/`: reusable workflow hooks.
- `src/lib/`: API clients, auth helpers, and contracts.
- `src/types/`: shared frontend types.

## Behavior-Preserving Cleanup Rules
- Keep existing route paths (`/`, `/product`) unchanged.
- Keep API contract usage aligned with backend payloads.
- Run production build after any structural cleanup.
