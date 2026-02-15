"""Targeted tests for orchestrator stage behavior."""

from __future__ import annotations

import pytest

from app.agents.orchestrator import verify_node
from app.schemas.agent_state import PipelineStage, VerificationResults


@pytest.mark.asyncio
async def test_verify_node_fails_fast_when_no_discovered_suppliers():
    state = {
        "parsed_requirements": {
            "product_type": "Custom tote bag",
            "material": "Cotton",
            "search_queries": ["cotton tote bag manufacturer"],
            "regional_searches": [],
            "clarifying_questions": [],
        },
        "discovery_results": {
            "suppliers": [],
            "filtered_suppliers": [],
            "sources_searched": ["google_places"],
            "sources_failed": [],
            "total_raw_results": 23,
            "deduplicated_count": 0,
            "regional_results": {},
            "intermediaries_resolved": 0,
            "search_rounds": 1,
            "market_intelligence": None,
            "discovery_briefing": "",
        },
    }

    result = await verify_node(state)

    assert result["current_stage"] == PipelineStage.FAILED.value
    assert "No viable suppliers were available after discovery filtering" in (result.get("error") or "")


@pytest.mark.asyncio
async def test_verify_node_keeps_explicit_all_checks_failed_error(monkeypatch):
    async def _empty_verify(*args, **kwargs):
        return VerificationResults(verifications=[])

    monkeypatch.setattr("app.agents.orchestrator.verify_suppliers", _empty_verify)

    state = {
        "parsed_requirements": {
            "product_type": "Custom tote bag",
            "material": "Cotton",
            "search_queries": ["cotton tote bag manufacturer"],
            "regional_searches": [],
            "clarifying_questions": [],
        },
        "discovery_results": {
            "suppliers": [
                {
                    "name": "Supplier A",
                    "website": "https://example.com",
                    "source": "google_places",
                    "relevance_score": 75,
                }
            ],
            "filtered_suppliers": [],
            "sources_searched": ["google_places"],
            "sources_failed": [],
            "total_raw_results": 5,
            "deduplicated_count": 1,
            "regional_results": {},
            "intermediaries_resolved": 0,
            "search_rounds": 1,
            "market_intelligence": None,
            "discovery_briefing": "",
        },
    }

    result = await verify_node(state)

    assert result["current_stage"] == PipelineStage.FAILED.value
    assert "all supplier checks returned errors" in (result.get("error") or "")
