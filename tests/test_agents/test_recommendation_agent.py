"""Tests for recommendation agent lane and trust behavior."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.recommendation_agent import generate_recommendation
from app.schemas.agent_state import (
    ComparisonResult,
    ParsedRequirements,
    SupplierComparison,
    SupplierVerification,
    VerificationCheck,
    VerificationResults,
)


def _build_requirements(product_type: str = "Custom tote bag") -> ParsedRequirements:
    return ParsedRequirements(
        product_type=product_type,
        material="Cotton canvas",
        quantity=1000,
        delivery_location="Austin, TX",
        missing_fields=[],
        search_queries=["custom tote bag manufacturer"],
    )


def _build_comparison() -> ComparisonResult:
    return ComparisonResult(
        comparisons=[
            SupplierComparison(
                supplier_name="Acme Mills",
                supplier_index=0,
                verification_score=92,
                overall_score=90,
                lead_time="20-25 days",
                strengths=["Strong verification"],
            ),
            SupplierComparison(
                supplier_name="Beta Works",
                supplier_index=1,
                verification_score=88,
                overall_score=85,
                lead_time="18-22 days",
                strengths=["Fast turnarounds"],
            ),
            SupplierComparison(
                supplier_name="Core Supply",
                supplier_index=2,
                verification_score=75,
                overall_score=78,
                lead_time="10-14 days",
                strengths=["Quick shipping"],
            ),
            SupplierComparison(
                supplier_name="Delta Global",
                supplier_index=3,
                verification_score=70,
                overall_score=72,
                lead_time="30-35 days",
                strengths=["Lower landed cost"],
            ),
        ]
    )


def _build_verifications() -> VerificationResults:
    return VerificationResults(
        verifications=[
            SupplierVerification(
                supplier_name="Acme Mills",
                supplier_index=0,
                checks=[VerificationCheck(check_type="website", status="passed", score=95)],
                composite_score=92,
                risk_level="low",
                recommendation="proceed",
            ),
            SupplierVerification(
                supplier_name="Beta Works",
                supplier_index=1,
                checks=[VerificationCheck(check_type="website", status="passed", score=88)],
                composite_score=88,
                risk_level="medium",
                recommendation="caution",
            ),
            SupplierVerification(
                supplier_name="Core Supply",
                supplier_index=2,
                checks=[VerificationCheck(check_type="website", status="passed", score=80)],
                composite_score=80,
                risk_level="low",
                recommendation="proceed",
            ),
            SupplierVerification(
                supplier_name="Delta Global",
                supplier_index=3,
                checks=[VerificationCheck(check_type="website", status="failed", score=40)],
                composite_score=40,
                risk_level="high",
                recommendation="reject",
            ),
        ]
    )


@pytest.mark.asyncio
@patch("app.agents.recommendation_agent.call_llm_structured", new_callable=AsyncMock)
async def test_recommendation_agent_accepts_full_lane_output(mock_llm, monkeypatch):
    from app.agents import recommendation_agent as module

    monkeypatch.setattr(module.settings, "feature_focus_circle_search_v1", True)
    mock_llm.return_value = json.dumps(
        {
            "executive_summary": "Strong options available.",
            "decision_checkpoint_summary": "Decision readiness is high.",
            "elimination_rationale": "Narrowed due to verification gaps.",
            "caveats": ["Confirm final sample before PO."],
            "recommendations": [
                {
                    "rank": 1,
                    "supplier_name": "Acme Mills",
                    "supplier_index": 0,
                    "overall_score": 90,
                    "confidence": "high",
                    "reasoning": "Balanced fit.",
                    "best_for": "best overall",
                    "lane": "best_overall",
                    "why_trust": ["Low risk with high verification score."],
                    "uncertainty_notes": ["Pricing still estimated."],
                    "verify_before_po": ["Request final production sample."],
                },
                {
                    "rank": 2,
                    "supplier_name": "Beta Works",
                    "supplier_index": 1,
                    "overall_score": 85,
                    "confidence": "medium",
                    "reasoning": "Fast response profile.",
                    "best_for": "fastest delivery",
                    "lane": "best_speed_to_order",
                    "why_trust": ["Strong responsiveness signal."],
                    "uncertainty_notes": [],
                    "verify_before_po": [],
                },
                {
                    "rank": 3,
                    "supplier_name": "Core Supply",
                    "supplier_index": 2,
                    "overall_score": 78,
                    "confidence": "medium",
                    "reasoning": "Reliable fallback option.",
                    "best_for": "best low risk",
                    "lane": "best_low_risk",
                    "why_trust": [],
                    "uncertainty_notes": [],
                    "verify_before_po": [],
                },
            ],
        }
    )

    result = await generate_recommendation(
        _build_requirements(),
        _build_comparison(),
        _build_verifications(),
    )

    assert result.recommendations
    assert result.decision_checkpoint_summary == "Decision readiness is high."
    assert result.elimination_rationale == "Narrowed due to verification gaps."
    assert result.lane_coverage.get("best_overall", 0) >= 1
    assert result.lane_coverage.get("best_low_risk", 0) >= 1
    assert result.lane_coverage.get("best_speed_to_order", 0) >= 1


@pytest.mark.asyncio
@patch("app.agents.recommendation_agent.call_llm_structured", new_callable=AsyncMock)
async def test_recommendation_agent_partial_output_triggers_lane_floor_and_rationale(mock_llm, monkeypatch):
    from app.agents import recommendation_agent as module

    monkeypatch.setattr(module.settings, "feature_focus_circle_search_v1", True)
    mock_llm.return_value = json.dumps(
        {
            "executive_summary": "One clear option found.",
            "recommendations": [
                {
                    "rank": 1,
                    "supplier_name": "Acme Mills",
                    "supplier_index": 0,
                    "overall_score": 90,
                    "confidence": "high",
                    "reasoning": "Top fit from model output.",
                    "best_for": "best overall",
                }
            ],
            "caveats": [],
        }
    )

    result = await generate_recommendation(
        _build_requirements(product_type="PCB assembly"),
        _build_comparison(),
        _build_verifications(),
    )

    assert len(result.recommendations) >= 3
    lanes = {rec.lane for rec in result.recommendations}
    assert "best_overall" in lanes
    assert "best_low_risk" in lanes
    assert "best_speed_to_order" in lanes
    assert result.elimination_rationale is not None
    assert result.decision_checkpoint_summary
    assert all(rec.needs_manual_verification for rec in result.recommendations)
