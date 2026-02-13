# Agent Tools (`app/agents/tools/`)

## Purpose
Provider and utility adapters used by agents (search, enrichment, intermediary detection, scraping).

## Cleanup Guidance
- Keep tool adapters thin and side-effect-aware.
- Normalize return payload shapes before exposing to agent logic.
- Add provider-failure fallbacks rather than silent exception swallowing.
