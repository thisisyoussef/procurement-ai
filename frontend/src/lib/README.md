# Frontend Library (`frontend/src/lib/`)

## Purpose
Client-side API/auth/contracts and feature-flag helpers.

## Modules
- `auth.ts`: auth session helpers and `authFetch` wrapper.
- `api/procurementClient.ts`: typed API adapter surface.
- `contracts/procurement.ts`: frontend contract types.
- `featureFlags.ts`: environment flag parsing and guard rails.

## Cleanup Guidance
- Keep backend contract mapping explicit and centralized.
- Prefer typed wrappers over ad-hoc fetch calls.
- Preserve compatibility with existing backend responses.
