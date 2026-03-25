# Frontend (`frontend/`)

## Purpose
Next.js application for Procurement AI landing and product workspace.

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
- Keep dashboard Active filtering aligned with backend active statuses, including `steering`.
- Dashboard supports a `Closed` preset mapped to terminal statuses (`complete`, `failed`, `canceled`) via `status=closed`.
- Dashboard project cards support title keyword filtering via `q` query param; preserve URL state with existing tab/status filters.
- Dashboard contacts support keyword filtering via `contacts_q` UI state and `q` on `/api/v1/dashboard/contacts`.
- Run production build after any structural cleanup.

## Tracing
- Client tracing defaults to enabled and records page/user actions to console and `/api/v1/events`.
- Disable by setting `NEXT_PUBLIC_PROCUREMENT_CLIENT_TRACING=false`.
