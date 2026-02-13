# Tests (`tests/`)

## Purpose
Regression safety net for API behavior, agent behavior, and contract-preserving refactors.

## Test Groups
- `tests/test_api/`: endpoint and workflow behavior checks.
- `tests/test_agents/`: agent-level behavior and merge logic checks.

## Refactor Safety Policy
- Refactors should keep existing tests passing.
- Add focused tests when moving shared logic across modules.
- Prefer deterministic fixtures and mocks over external network calls.
