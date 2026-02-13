# Components (`frontend/src/components/`)

## Purpose
Shared UI and workflow components for landing/product experiences.

## Structure
- Generic workflow components (`SearchForm`, `SupplierResults`, `OutreachPanel`, etc.).
- Workspace-specific shell/components under `workspace/`.

## Cleanup Guidance
- Favor presentational components with explicit props.
- Keep data-fetch logic in hooks/context where possible.
- Maintain current copy and user-facing behavior during cleanup.
