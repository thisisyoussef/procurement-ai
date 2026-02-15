"""Direct manufacturer hunt team."""

from __future__ import annotations

from app.agents.supplier_discovery import discover_suppliers as legacy_discover_suppliers
from app.schemas.agent_state import ParsedRequirements
from app.schemas.buyer_context import BuyerContext

from .aggregator import TeamResult
from .strategy_selector import DiscoveryTeam


async def run_direct_manufacturer_search(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> TeamResult:
    tuned = requirements.model_copy(deep=True)
    product = requirements.product_type or "product"
    tuned.search_queries = list(dict.fromkeys(
        [
            f"{product} factory",
            f"{product} OEM manufacturer",
            f"{product} production facility",
            *(requirements.search_queries or []),
        ]
    ))

    results = await legacy_discover_suppliers(tuned, buyer_context=buyer_context)
    for supplier in results.suppliers:
        supplier.discovery_teams = sorted({*(supplier.discovery_teams or []), DiscoveryTeam.DIRECT_MANUFACTURER.value})
        supplier.manufacturing_confidence = max(supplier.manufacturing_confidence, min(100.0, supplier.relevance_score + 10.0))

    return TeamResult(
        team=DiscoveryTeam.DIRECT_MANUFACTURER,
        suppliers=results.suppliers,
        coverage_notes="Direct manufacturer lens",
        confidence=0.72,
    )
