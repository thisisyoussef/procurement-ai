"""Regional deep-dive team."""

from __future__ import annotations

from app.agents.supplier_discovery import discover_suppliers as legacy_discover_suppliers
from app.schemas.agent_state import ParsedRequirements, RegionalSearchConfig
from app.schemas.buyer_context import BuyerContext

from .aggregator import TeamResult
from .strategy_selector import DiscoveryTeam


async def run_regional_deep_dive(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
    regions: list[RegionalSearchConfig],
) -> TeamResult:
    tuned = requirements.model_copy(deep=True)
    tuned.regional_searches = regions[:3]

    results = await legacy_discover_suppliers(tuned, buyer_context=buyer_context)
    for supplier in results.suppliers:
        supplier.discovery_teams = sorted({*(supplier.discovery_teams or []), DiscoveryTeam.REGIONAL_DEEP_DIVE.value})
        supplier.regional_depth_score = max(
            supplier.regional_depth_score,
            75.0 if supplier.language_discovered and supplier.language_discovered != "en" else 55.0,
        )

    return TeamResult(
        team=DiscoveryTeam.REGIONAL_DEEP_DIVE,
        suppliers=results.suppliers,
        coverage_notes="Localized search depth",
        confidence=0.63,
    )
