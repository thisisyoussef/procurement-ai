"""Market intelligence sweep team."""

from __future__ import annotations

from app.agents.supplier_discovery import discover_suppliers as legacy_discover_suppliers
from app.schemas.agent_state import MarketIntelligence, ParsedRequirements
from app.schemas.buyer_context import BuyerContext

from .aggregator import TeamResult
from .strategy_selector import DiscoveryTeam


async def run_market_intelligence_sweep(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> TeamResult:
    tuned = requirements.model_copy(deep=True)
    product = requirements.product_type or "product"
    tuned.search_queries = list(dict.fromkeys(
        [
            f"{product} marketplace supplier",
            f"{product} wholesale listing",
            f"{product} RFQ supplier",
            *(requirements.search_queries or []),
        ]
    ))

    results = await legacy_discover_suppliers(tuned, buyer_context=buyer_context)
    for supplier in results.suppliers:
        supplier.discovery_teams = sorted({*(supplier.discovery_teams or []), DiscoveryTeam.MARKET_INTELLIGENCE.value})
        supplier.market_position = max(supplier.market_position, min(100.0, supplier.relevance_score))

    market = results.market_intelligence or MarketIntelligence(
        dominant_regions=sorted({s.country for s in results.suppliers if s.country})[:6],
        common_certifications=sorted({c for s in results.suppliers for c in (s.certifications or [])})[:8],
        market_maturity=("mature" if len(results.suppliers) >= 15 else "growing" if len(results.suppliers) >= 8 else "emerging"),
    )

    return TeamResult(
        team=DiscoveryTeam.MARKET_INTELLIGENCE,
        suppliers=results.suppliers,
        market_intelligence=market,
        coverage_notes="Market breadth and pricing signals",
        confidence=0.68,
    )
