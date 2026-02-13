# Frontend Source Map (`frontend/src/`)

## Route to Feature Flow
1. Landing route (`app/page.tsx`) drives top-of-funnel intake.
2. Product route (`app/product/page.tsx`) hosts workspace shell.
3. Workspace context (`contexts/WorkspaceContext.tsx`) owns project/session state.
4. Phase components in `components/workspace/phases/` render pipeline stages.
5. API/auth access via `lib/` helpers.

## Cleanup Priorities
- Reduce duplicated formatting/styling patterns.
- Keep phase contracts explicit and typed.
- Preserve current user flow and messaging behavior.
