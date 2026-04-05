"""Tests for the Requirements Parser agent."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.agents.requirements_parser import parse_requirements
from app.schemas.agent_state import ParsedRequirements


MOCK_LLM_RESPONSE = json.dumps({
    "product_type": "tote bag",
    "material": "12oz cotton canvas",
    "dimensions": "14x16 inches",
    "quantity": 500,
    "customization": "screen print, 2 colors, custom logo",
    "delivery_location": "Los Angeles, CA",
    "deadline": "2026-03-01",
    "certifications_needed": [],
    "budget_range": None,
    "missing_fields": ["budget_range"],
    "search_queries": [
        "custom canvas tote bag manufacturer Los Angeles",
        "tote bag supplier wholesale USA",
        "cotton canvas tote bag factory custom printing",
    ],
})


@pytest.mark.asyncio
@patch("app.agents.requirements_parser.call_llm_structured", new_callable=AsyncMock)
async def test_parse_requirements_basic(mock_llm):
    """Test that the parser correctly extracts structured requirements."""
    mock_llm.return_value = MOCK_LLM_RESPONSE

    result = await parse_requirements(
        "I need 500 custom canvas tote bags, 14x16 inches, 12oz cotton canvas, "
        "screen printed with my logo in 2 colors, delivered to LA by March 2026"
    )

    assert isinstance(result, ParsedRequirements)
    assert result.product_type == "tote bag"
    assert result.quantity == 500
    assert result.material == "12oz cotton canvas"
    assert len(result.search_queries) >= 3
    assert "budget_range" in result.missing_fields


@pytest.mark.asyncio
@patch("app.agents.requirements_parser.call_llm_structured", new_callable=AsyncMock)
async def test_parse_requirements_handles_bad_json(mock_llm):
    """Test graceful handling of invalid JSON from LLM."""
    mock_llm.return_value = "This is not valid JSON at all"

    result = await parse_requirements("some product description")

    assert isinstance(result, ParsedRequirements)
    assert result.product_type == "unknown"


@pytest.mark.asyncio
@patch("app.agents.requirements_parser.call_llm_structured", new_callable=AsyncMock)
async def test_parse_requirements_handles_markdown_wrapped_json(mock_llm):
    """Test that parser handles JSON wrapped in markdown code blocks."""
    mock_llm.return_value = f"```json\n{MOCK_LLM_RESPONSE}\n```"

    result = await parse_requirements("500 custom tote bags")

    assert isinstance(result, ParsedRequirements)
    assert result.product_type == "tote bag"


@pytest.mark.asyncio
@patch("app.agents.requirements_parser.call_llm_structured", new_callable=AsyncMock)
async def test_parse_requirements_rebuilds_when_category_is_not_in_user_input(mock_llm):
    """If the model leaks a mismatched category, parser should rebuild from raw user intent."""
    mock_llm.return_value = MOCK_LLM_RESPONSE

    result = await parse_requirements(
        "Need 200 injection molded ABS enclosures for an electronics controller."
    )

    assert isinstance(result, ParsedRequirements)
    assert "tote" not in result.product_type.lower()
    assert result.search_queries
    assert all("tote" not in q.lower() for q in result.search_queries)
    assert any("manufacturer" in q.lower() for q in result.search_queries)


@pytest.mark.asyncio
@patch("app.agents.requirements_parser.call_llm_structured", new_callable=AsyncMock)
async def test_parse_requirements_keeps_grounded_product_type_and_queries(mock_llm):
    mock_llm.return_value = MOCK_LLM_RESPONSE

    result = await parse_requirements(
        "Need 500 custom cotton tote bags for a conference giveaway."
    )

    assert isinstance(result, ParsedRequirements)
    assert "tote" in result.product_type.lower()
    assert result.search_queries == [
        "custom canvas tote bag manufacturer Los Angeles",
        "tote bag supplier wholesale USA",
        "cotton canvas tote bag factory custom printing",
    ]


@pytest.mark.asyncio
@patch("app.agents.requirements_parser.call_llm_structured", new_callable=AsyncMock)
async def test_parse_requirements_rebuilds_queries_when_category_mismatch(mock_llm):
    mock_llm.return_value = json.dumps(
        {
            "product_type": "tote bag",
            "quantity": 200,
            "search_queries": ["buy tote bags online", "tote bag retail store near me"],
            "missing_fields": ["material"],
        }
    )

    result = await parse_requirements("Need 200 CNC machined aluminum brackets for robotics.")

    assert isinstance(result, ParsedRequirements)
    assert "tote" not in result.product_type.lower()
    assert result.search_queries
    assert all("tote" not in q.lower() for q in result.search_queries)
    assert any("manufacturer" in q.lower() for q in result.search_queries)


@pytest.mark.asyncio
@patch("app.agents.requirements_parser.call_llm_structured", new_callable=AsyncMock)
async def test_parse_requirements_backfills_clarifying_question_guidance(mock_llm, monkeypatch):
    from app.agents import requirements_parser as parser_module

    monkeypatch.setattr(parser_module.settings, "feature_focus_circle_search_v1", True)
    mock_llm.return_value = json.dumps(
        {
            "product_type": "Custom tote bag",
            "material": "Cotton canvas",
            "dimensions": None,
            "quantity": None,
            "customization": "Screen print",
            "delivery_location": None,
            "deadline": None,
            "certifications_needed": [],
            "budget_range": None,
            "missing_fields": ["quantity", "budget_range"],
            "search_queries": ["custom tote bag manufacturer"],
            "clarifying_questions": [
                {
                    "field": "quantity",
                    "question": "How many units do you need?",
                    "importance": "recommended",
                    "suggestions": ["500", "1000"],
                },
                {
                    "field": "trade_off_priority",
                    "question": "What matters most?",
                    "importance": "recommended",
                    "suggestions": [],
                },
            ],
        }
    )

    result = await parse_requirements("Need custom tote bags with logo")

    assert result.clarifying_questions
    assert result.clarifying_questions[0].why_this_question
    assert result.clarifying_questions[0].if_skipped_impact
    assert result.clarifying_questions[0].suggested_default == "500"
    assert result.clarifying_questions[1].suggested_default is not None
