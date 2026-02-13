# Frontend Types (`frontend/src/types/`)

## Purpose
Shared type definitions for pipeline phases and status mapping.

## Current File
- `pipeline.ts`: stage-to-phase mapping, phase access rules, and status interfaces.

## Cleanup Guidance
- Keep stage/phase mapping in sync with backend stage names.
- Treat type changes as behavior-sensitive when they alter rendering gates.
