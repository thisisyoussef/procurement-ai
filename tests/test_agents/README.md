# Agent Tests (`tests/test_agents/`)

## Covered Areas
- Requirements parsing heuristics.
- Supplier discovery + supplier-memory merge behavior.

## Expectations During Cleanup
- Preserve supplier-memory-first discovery semantics.
- Preserve deduplication and merge behavior.
- Add targeted tests before changing scoring/selection logic.
