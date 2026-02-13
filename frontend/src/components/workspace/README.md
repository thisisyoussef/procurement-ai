# Workspace Components (`frontend/src/components/workspace/`)

## Purpose
Primary product shell and phase rendering for `/product`.

## Key Modules
- `WorkspaceShell.tsx`: overall layout container.
- `LeftRail.tsx`: project navigation and status.
- `PhaseTabBar.tsx`: phase switching.
- `CenterStage.tsx`: active phase renderer.
- `phases/*`: stage-specific UIs (brief/search/compare/outreach/samples/order).

## Cleanup Guidance
- Preserve current phase order and accessibility logic.
- Keep cancel/new/open project controls behavior intact.
- Keep outreach approval flow as current single decision UX.
