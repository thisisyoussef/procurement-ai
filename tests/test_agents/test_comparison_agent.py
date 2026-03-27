"""Tests for comparison agent shipping sanity guards."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.comparison_agent import compare_suppliers
from app.schemas.agent_state import (
    DiscoveredSupplier,
    ParsedRequirements,
    SupplierVerification,
    VerificationCheck,
    VerificationResults,
)


def _build_verifications() -> VerificationResults:
    return VerificationResults(
        verifications=[
            SupplierVerification(
                supplier_name="RubberCo",
                supplier_index=0,
                checks=[VerificationCheck(check_type="website", status="passed", score=85)],
                composite_score=85,
                risk_level="medium",
                recommendation="proceed",
            )
        ]
    )


def _build_requirements(quantity: int | None) -> ParsedRequirements:
    return ParsedRequirements(
        product_type="Rubber compound for car tires",
        material="Synthetic rubber",
        quantity=quantity,
        delivery_location="Detroit, MI",
        missing_fields=[],
        search_queries=["tire rubber manufacturer"],
    )


def _build_suppliers() -> list[DiscoveredSupplier]:
    return [DiscoveredSupplier(
        name="RubberCo",
        country="Thailand",
        city="Rayong",
        description="Synthetic rubber compound manufacturer for car tires and automotive applications",
        categories=["rubber", "tires", "automotive"],
    )]


def _build_domestic_suppliers() -> list[DiscoveredSupplier]:
    return [DiscoveredSupplier(
        name="RubberCo",
        country="United States",
        city="Akron",
        description="Synthetic rubber compound manufacturer for car tires and automotive applications",
        categories=["rubber", "tires", "automotive"],
    )]


@pytest.mark.asyncio
@patch("app.agents.comparison_agent.call_llm_structured", new_callable=AsyncMock)
async def test_comparison_agent_flags_unrealistically_low_heavy_shipping(mock_llm):
    mock_llm.return_value = json.dumps(
        {
            "comparisons": [
                {
                    "supplier_name": "RubberCo",
                    "supplier_index": 0,
                    "verification_score": 85,
                    "estimated_unit_price": "$1.80-$2.20",
                    "estimated_shipping_cost": "$0.30-$0.80 per unit",
                    "estimated_landed_cost": "$2.10-$3.00 per unit",
                    "moq": "5000",
                    "lead_time": "20-30 days",
                    "certifications": ["ISO 9001"],
                    "strengths": ["Large capacity"],
                    "weaknesses": [],
                    "overall_score": 82,
                    "price_score": 4.0,
                    "quality_score": 3.8,
                    "shipping_score": 4.2,
                    "review_score": 3.5,
                    "lead_time_score": 3.0,
                }
            ],
            "analysis_narrative": "Initial analysis.",
            "best_value": "RubberCo",
            "best_quality": "RubberCo",
            "best_speed": "RubberCo",
        }
    )

    result = await compare_suppliers(_build_requirements(quantity=3000), _build_suppliers(), _build_verifications())

    assert result.comparisons
    row = result.comparisons[0]
    assert row.estimated_shipping_cost is not None
    assert "Freight quote required" in row.estimated_shipping_cost
    assert any("freight" in weakness.lower() for weakness in row.weaknesses)
    assert row.estimated_landed_cost == "Freight quote required to finalize landed cost"
    assert "converted to quote-required" in result.analysis_narrative


@pytest.mark.asyncio
@patch("app.agents.comparison_agent.call_llm_structured", new_callable=AsyncMock)
async def test_comparison_agent_allows_low_per_unit_for_high_volume(mock_llm):
    mock_llm.return_value = json.dumps(
        {
            "comparisons": [
                {
                    "supplier_name": "RubberCo",
                    "supplier_index": 0,
                    "verification_score": 85,
                    "estimated_unit_price": "$1.80-$2.20",
                    "estimated_shipping_cost": "$0.30-$0.80 per unit",
                    "estimated_landed_cost": "$2.10-$3.00 per unit",
                    "moq": "50000",
                    "lead_time": "20-30 days",
                    "certifications": ["ISO 9001"],
                    "strengths": ["Large capacity"],
                    "weaknesses": [],
                    "overall_score": 82,
                    "price_score": 4.0,
                    "quality_score": 3.8,
                    "shipping_score": 4.2,
                    "review_score": 3.5,
                    "lead_time_score": 3.0,
                }
            ],
            "analysis_narrative": "Initial analysis.",
            "best_value": "RubberCo",
            "best_quality": "RubberCo",
            "best_speed": "RubberCo",
        }
    )

    result = await compare_suppliers(_build_requirements(quantity=50000), _build_suppliers(), _build_verifications())

    assert result.comparisons
    row = result.comparisons[0]
    assert row.estimated_shipping_cost == "$0.30-$0.80 per unit"
    assert row.estimated_landed_cost == "$2.10-$3.00 per unit"


@pytest.mark.asyncio
@patch("app.agents.comparison_agent.call_llm_structured", new_callable=AsyncMock)
async def test_comparison_agent_keeps_low_per_unit_for_domestic_lane(mock_llm):
    mock_llm.return_value = json.dumps(
        {
            "comparisons": [
                {
                    "supplier_name": "RubberCo",
                    "supplier_index": 0,
                    "verification_score": 85,
                    "estimated_unit_price": "$1.80-$2.20",
                    "estimated_shipping_cost": "$0.30-$0.80 per unit",
                    "estimated_landed_cost": "$2.10-$3.00 per unit",
                    "moq": "3000",
                    "lead_time": "10-14 days",
                    "certifications": ["ISO 9001"],
                    "strengths": ["Domestic trucking network"],
                    "weaknesses": [],
                    "overall_score": 84,
                    "price_score": 4.0,
                    "quality_score": 4.0,
                    "shipping_score": 4.1,
                    "review_score": 3.9,
                    "lead_time_score": 4.3,
                }
            ],
            "analysis_narrative": "Domestic supplier analysis.",
            "best_value": "RubberCo",
            "best_quality": "RubberCo",
            "best_speed": "RubberCo",
        }
    )

    result = await compare_suppliers(
        _build_requirements(quantity=3000), _build_domestic_suppliers(), _build_verifications()
    )

    assert result.comparisons
    row = result.comparisons[0]
    assert row.estimated_shipping_cost == "$0.30-$0.80 per unit"
    assert row.estimated_landed_cost == "$2.10-$3.00 per unit"
    assert "converted to quote-required" not in result.analysis_narrative
