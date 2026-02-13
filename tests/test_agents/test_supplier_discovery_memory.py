from unittest.mock import AsyncMock

import pytest

from app.agents import supplier_discovery
from app.schemas.agent_state import DiscoveredSupplier, ParsedRequirements


@pytest.mark.asyncio
async def test_discovery_merges_supplier_memory_results(monkeypatch):
    requirements = ParsedRequirements(
        product_type="hoodies",
        search_queries=["heavyweight hoodie manufacturer"],
    )

    web_supplier = DiscoveredSupplier(
        name="Acme Garments",
        website="https://acme.com",
        source="google_places",
        relevance_score=62,
    )
    memory_supplier = DiscoveredSupplier(
        supplier_id="11111111-1111-1111-1111-111111111111",
        name="ACME Garments Ltd",
        website="http://www.acme.com",
        source="supplier_memory",
        relevance_score=74,
    )

    monkeypatch.setattr(supplier_discovery, "_search_google", AsyncMock(return_value=[{"name": "Acme"}]))
    monkeypatch.setattr(supplier_discovery, "_search_web", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_marketplaces", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_supplier_memory", AsyncMock(return_value=[memory_supplier]))
    monkeypatch.setattr(supplier_discovery, "_score_and_deduplicate", AsyncMock(return_value=[web_supplier]))
    monkeypatch.setattr(
        supplier_discovery,
        "_filter_and_resolve_intermediaries",
        AsyncMock(side_effect=lambda suppliers, _requirements: (suppliers, 0)),
    )
    monkeypatch.setattr(supplier_discovery, "_should_expand_search", lambda *_: (False, ""))

    result = await supplier_discovery.discover_suppliers(requirements)

    assert len(result.suppliers) == 1
    merged = result.suppliers[0]
    assert merged.supplier_id == "11111111-1111-1111-1111-111111111111"
    assert "supplier_memory" in merged.source
    assert "supplier_memory" in result.sources_searched


@pytest.mark.asyncio
async def test_discovery_returns_memory_only_results_when_web_is_empty(monkeypatch):
    requirements = ParsedRequirements(product_type="custom packaging")
    memory_supplier = DiscoveredSupplier(
        supplier_id="22222222-2222-2222-2222-222222222222",
        name="Atlas Packaging",
        source="supplier_memory",
        relevance_score=68,
    )

    monkeypatch.setattr(supplier_discovery, "_search_google", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_web", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_marketplaces", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_supplier_memory", AsyncMock(return_value=[memory_supplier]))
    monkeypatch.setattr(
        supplier_discovery,
        "_filter_and_resolve_intermediaries",
        AsyncMock(side_effect=lambda suppliers, _requirements: (suppliers, 0)),
    )
    monkeypatch.setattr(supplier_discovery, "_should_expand_search", lambda *_: (False, ""))

    result = await supplier_discovery.discover_suppliers(requirements)

    assert len(result.suppliers) == 1
    assert result.suppliers[0].name == "Atlas Packaging"
    assert result.sources_searched == ["supplier_memory"]


@pytest.mark.asyncio
async def test_discovery_checks_supplier_memory_before_external_search(monkeypatch):
    requirements = ParsedRequirements(
        product_type="automotive stamping supplier",
        search_queries=["automotive stamping supplier"],
    )
    memory_supplier = DiscoveredSupplier(
        supplier_id="33333333-3333-3333-3333-333333333333",
        name="Memory Metals",
        source="supplier_memory",
        relevance_score=72,
    )

    call_order: list[str] = []

    async def _memory_first(*_args, **_kwargs):
        call_order.append("memory")
        return [memory_supplier]

    async def _google(*_args, **_kwargs):
        call_order.append("google")
        return []

    async def _web(*_args, **_kwargs):
        call_order.append("web")
        return []

    async def _marketplaces(*_args, **_kwargs):
        call_order.append("marketplaces")
        return []

    monkeypatch.setattr(supplier_discovery, "_search_supplier_memory", _memory_first)
    monkeypatch.setattr(supplier_discovery, "_search_google", _google)
    monkeypatch.setattr(supplier_discovery, "_search_web", _web)
    monkeypatch.setattr(supplier_discovery, "_search_marketplaces", _marketplaces)
    monkeypatch.setattr(
        supplier_discovery,
        "_filter_and_resolve_intermediaries",
        AsyncMock(side_effect=lambda suppliers, _requirements: (suppliers, 0)),
    )
    monkeypatch.setattr(supplier_discovery, "_should_expand_search", lambda *_: (False, ""))

    result = await supplier_discovery.discover_suppliers(requirements)

    assert call_order
    assert call_order[0] == "memory"
    assert "supplier_memory" in result.sources_searched
    assert result.suppliers and result.suppliers[0].name == "Memory Metals"
