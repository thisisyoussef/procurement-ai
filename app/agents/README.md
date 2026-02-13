# Agents (`app/agents/`)

## Purpose
LLM-assisted pipeline logic for requirements parsing, discovery, verification, comparison, recommendation, outreach, follow-up, response parsing, and chat actions.

## Files
- `orchestrator.py`: stage graph and node wiring.
- `requirements_parser.py`: brief parsing and clarification prompts.
- `supplier_discovery.py`: hybrid discovery (memory + web sources).
- `supplier_verifier.py`: verification and risk scoring.
- `comparison_agent.py` + `recommendation_agent.py`: evaluation and ranking.
- `outreach_agent.py` + `followup_agent.py` + `response_parser.py`: outreach lifecycle.
- `chat_agent.py`: interactive workflow adjustments.

## Cleanup Guidance
- Keep stage contracts stable (`GraphState` and schema payloads).
- Isolate provider-specific side effects from pure scoring/transform logic.
- Preserve deterministic fallback behavior when LLM output is malformed.
