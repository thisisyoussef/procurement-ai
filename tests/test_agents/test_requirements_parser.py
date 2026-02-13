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
