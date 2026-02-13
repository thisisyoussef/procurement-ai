# Contexts (`frontend/src/contexts/`)

## Purpose
Shared runtime state containers for workspace features.

## Current Contexts
- `WorkspaceContext.tsx`: project lifecycle, polling, active phase state, error handling, and user session wiring.

## Cleanup Guidance
- Keep state transition side effects deterministic.
- Avoid mixing view rendering concerns into context actions.
- Preserve URL query parameter behavior (`projectId` syncing).
