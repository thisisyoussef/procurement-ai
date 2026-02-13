# Refactoring Plan (Behavior-Preserving)

## Goal
Perform a major structural cleanup without changing runtime behavior, API contracts, business rules, or user-visible outputs.

## Non-Goals
- No endpoint removals or response-shape changes.
- No pipeline stage reordering.
- No UI flow changes.
- No migration rewrites that alter existing data semantics.

## Invariants
- Existing API routes remain backward-compatible.
- Existing project lifecycle states remain unchanged.
- Existing outreach auto/manual decision model remains unchanged.
- Existing tests continue passing before and after each phase.

## Phase 0: Baseline and Guardrails
- Add folder-level documentation and ownership boundaries.
- Document shared contracts (`schemas`, frontend `contracts`).
- Freeze baseline through test/build checks.

## Phase 1: Backend Structural Separation
- Separate route handlers, orchestration, and persistence responsibilities.
- Reduce cross-layer imports (API -> services -> repositories).
- Standardize helper naming (`_get_*`, `_save_*`, `_normalize_*`).

## Phase 2: Agent and Workflow Cleanup
- Consolidate repeated matching/merge logic.
- Isolate provider-specific integrations behind service interfaces.
- Add consistent stage-level progress telemetry boundaries.

## Phase 3: Frontend Modular Cleanup
- Clarify route-level vs workspace-level responsibilities.
- Standardize phase component conventions and prop contracts.
- Tighten shared UI token usage (color, surface, typography classes).

## Phase 4: Data and Memory Layer Hardening
- Align supplier memory writes and read-first query boundaries.
- Document canonical persistence order (discover -> verify -> interact).
- Add regression checks around memory-first discovery behavior.

## Phase 5: Test and Observability Alignment
- Expand targeted regression tests per phase.
- Normalize logging event names and failure-path assertions.
- Add runbooks for common production failure scenarios.

## Acceptance Criteria
- All existing tests pass.
- Frontend production build passes.
- No route or schema behavior deltas.
- Clear docs exist for each major directory.
