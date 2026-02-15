"""Proximity and logistics-focused discovery team."""

from __future__ import annotations

from app.agents.supplier_discovery import discover_suppliers as legacy_discover_suppliers
from app.schemas.agent_state import ParsedRequirements
from app.schemas.buyer_context import BuyerContext

from .aggregator import TeamResult
from .strategy_selector import DiscoveryTeam


def _is_nearshore(country: str | None, destination: str | None) -> bool:
    if not country or not destination:
        return False
    c = country.lower()
    d = destination.lower()
    if "united states" in d or "usa" in d or "us" in d:
        return c in {"mexico", "canada"}
    return False


async def run_proximity_logistics_search(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> TeamResult:
    tuned = requirements.model_copy(deep=True)
    destination = requirements.delivery_location or buyer_context.logistics.shipping_country or ""
    product = requirements.product_type or "product"
    tuned.search_queries = list(dict.fromkeys(
        [
            f"{product} domestic manufacturer {destination}".strip(),
            f"{product} nearshore supplier {destination}".strip(),
            *(requirements.search_queries or []),
        ]
    ))

    results = await legacy_discover_suppliers(tuned, buyer_context=buyer_context)
    for supplier in results.suppliers:
        supplier.discovery_teams = sorted({*(supplier.discovery_teams or []), DiscoveryTeam.PROXIMITY_LOGISTICS.value})
        score = 40.0
        if destination and supplier.country and supplier.country.lower() in destination.lower():
            score += 40.0
        elif _is_nearshore(supplier.country, destination):
            score += 25.0
        supplier.logistics_fit = max(supplier.logistics_fit, min(100.0, score))

    return TeamResult(
        team=DiscoveryTeam.PROXIMITY_LOGISTICS,
        suppliers=results.suppliers,
        coverage_notes="Lead-time and shipping fit",
        confidence=0.66,
    )
