from unittest.mock import AsyncMock

import pytest

from app.agents import supplier_discovery
from app.schemas.agent_state import DiscoveredSupplier, ParsedRequirements


def _fake_raw(name: str, url: str) -> dict:
    return {"name": name, "url": url, "description": f"{name} factory"}


@pytest.mark.asyncio
async def test_discovery_merges_supplier_memory_results(monkeypatch):
    requirements = ParsedRequirements(
        product_type="hoodies",
        search_queries=["heavyweight hoodie manufacturer"],
    )

    web_supplier = DiscoveredSupplier(
        name="Acme Garments",
        website="https://acme.com",
        description="OEM hoodie and sweatshirt factory",
        categories=["hoodies", "apparel"],
        source="google_places",
        relevance_score=62,
    )
    memory_supplier = DiscoveredSupplier(
        supplier_id="11111111-1111-1111-1111-111111111111",
        name="ACME Garments Ltd",
        website="http://www.acme.com",
        description="Heavyweight hoodie manufacturer",
        categories=["hoodies", "garment factory"],
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


@pytest.mark.asyncio
async def test_discovery_filters_cross_category_memory_suppliers(monkeypatch):
    requirements = ParsedRequirements(
        product_type="heavyweight hoodies",
        search_queries=["heavyweight hoodie manufacturer"],
    )
    packaging_supplier = DiscoveredSupplier(
        supplier_id="44444444-4444-4444-4444-444444444444",
        name="Atlas Packaging Group",
        description="Custom boxes, labels, and packaging solutions",
        categories=["packaging", "labels"],
        source="supplier_memory",
        relevance_score=80,
    )
    hoodie_supplier = DiscoveredSupplier(
        supplier_id="55555555-5555-5555-5555-555555555555",
        name="Northstar Apparel Factory",
        description="OEM cut-and-sew hoodie manufacturer with embroidery",
        categories=["hoodies", "apparel"],
        source="supplier_memory",
        relevance_score=76,
    )

    monkeypatch.setattr(supplier_discovery, "_search_google", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_web", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_marketplaces", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        supplier_discovery,
        "_search_supplier_memory",
        AsyncMock(return_value=[packaging_supplier, hoodie_supplier]),
    )
    monkeypatch.setattr(
        supplier_discovery,
        "_filter_and_resolve_intermediaries",
        AsyncMock(side_effect=lambda suppliers, _requirements: (suppliers, 0)),
    )
    monkeypatch.setattr(supplier_discovery, "_should_expand_search", lambda *_: (False, ""))

    result = await supplier_discovery.discover_suppliers(requirements)

    assert [s.name for s in result.suppliers] == ["Northstar Apparel Factory"]
    assert any(s.name == "Atlas Packaging Group" and s.filtered_reason == "wrong_product_type" for s in result.filtered_suppliers)


@pytest.mark.asyncio
async def test_discovery_keeps_sparse_memory_supplier_when_metadata_is_missing(monkeypatch):
    requirements = ParsedRequirements(
        product_type="heavyweight hoodies",
        search_queries=["heavyweight hoodie manufacturer"],
    )
    sparse_supplier = DiscoveredSupplier(
        supplier_id="66666666-6666-6666-6666-666666666666",
        name="Legacy Supplier Record",
        description=None,
        categories=[],
        source="supplier_memory",
        relevance_score=59,
    )

    monkeypatch.setattr(supplier_discovery, "_search_google", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_web", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_marketplaces", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        supplier_discovery,
        "_search_supplier_memory",
        AsyncMock(return_value=[sparse_supplier]),
    )
    monkeypatch.setattr(
        supplier_discovery,
        "_filter_and_resolve_intermediaries",
        AsyncMock(side_effect=lambda suppliers, _requirements: (suppliers, 0)),
    )
    monkeypatch.setattr(supplier_discovery, "_should_expand_search", lambda *_: (False, ""))

    result = await supplier_discovery.discover_suppliers(requirements)

    assert [s.name for s in result.suppliers] == ["Legacy Supplier Record"]
    assert result.filtered_suppliers == []


def test_should_expand_when_below_surface_target():
    requirements = ParsedRequirements(product_type="hoodies")
    suppliers = [
        DiscoveredSupplier(name=f"Supplier {i}", relevance_score=70)
        for i in range(supplier_discovery.TARGET_SURFACED_SUPPLIERS_MIN - 1)
    ]

    should_expand, reason = supplier_discovery._should_expand_search(suppliers, requirements)

    assert should_expand is True
    assert reason == "below_target_final_count"


@pytest.mark.asyncio
async def test_discovery_reports_dedup_count_before_filtering(monkeypatch):
    requirements = ParsedRequirements(
        product_type="heavyweight hoodies",
        search_queries=["heavyweight hoodie manufacturer"],
    )

    valid_supplier = DiscoveredSupplier(
        name="Northstar Apparel Factory",
        website="https://northstar.example",
        description="OEM hoodie manufacturer",
        categories=["hoodies", "apparel"],
        source="google_places",
        relevance_score=72,
    )
    off_category_supplier = DiscoveredSupplier(
        name="Atlas Packaging Group",
        website="https://atlaspack.example",
        description="Packaging and labels provider",
        categories=["packaging", "labels"],
        source="firecrawl_web",
        relevance_score=66,
    )

    monkeypatch.setattr(
        supplier_discovery,
        "_search_google",
        AsyncMock(return_value=[_fake_raw("Northstar Apparel Factory", "https://northstar.example")]),
    )
    monkeypatch.setattr(
        supplier_discovery,
        "_search_web",
        AsyncMock(return_value=[_fake_raw("Atlas Packaging Group", "https://atlaspack.example")]),
    )
    monkeypatch.setattr(supplier_discovery, "_search_marketplaces", AsyncMock(return_value=[]))
    monkeypatch.setattr(supplier_discovery, "_search_supplier_memory", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        supplier_discovery,
        "_score_and_deduplicate",
        AsyncMock(return_value=[valid_supplier, off_category_supplier]),
    )
    monkeypatch.setattr(
        supplier_discovery,
        "_filter_and_resolve_intermediaries",
        AsyncMock(side_effect=lambda suppliers, _requirements: (suppliers, 0)),
    )
    monkeypatch.setattr(supplier_discovery, "_should_expand_search", lambda *_: (False, ""))

    result = await supplier_discovery.discover_suppliers(requirements)

    assert len(result.suppliers) == 1
    assert len(result.filtered_suppliers) == 1
    assert result.deduplicated_count == 2
