# Hooks (`frontend/src/hooks/`)

## Purpose
Reusable async/state logic shared across components.

## Current Hooks
- `usePipelinePolling.ts`: status polling loop and lifecycle.
- `useChat.ts`: chat interaction state/actions.
- `useOutreach.ts`: outreach interaction state/actions.

## Cleanup Guidance
- Keep hook return contracts stable for existing components.
- Avoid hidden side effects beyond documented actions.
- Add targeted tests when hook logic expands significantly.
