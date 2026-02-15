"""Resilience tests for supplier verifier."""

from __future__ import annotations

import pytest

from app.agents.supplier_verifier import verify_suppliers
from app.schemas.agent_state import DiscoveredSupplier


@pytest.mark.asyncio
async def test_verify_suppliers_returns_structured_failures_when_verify_crashes(monkeypatch):
    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated verifier outage")

    monkeypatch.setattr("app.agents.supplier_verifier.verify_supplier", _boom)

    suppliers = [
        DiscoveredSupplier(name="Supplier A", website="https://a.example", source="test", relevance_score=80),
        DiscoveredSupplier(name="Supplier B", website="https://b.example", source="test", relevance_score=70),
    ]

    result = await verify_suppliers(suppliers, max_concurrent=2)

    assert len(result.verifications) == 2
    assert all(v.risk_level == "high" for v in result.verifications)
    assert all(v.composite_score == 0 for v in result.verifications)
    assert all(v.checks and v.checks[0].check_type == "verification_error" for v in result.verifications)
