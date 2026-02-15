"""Multi-team supplier discovery entrypoint."""

from __future__ import annotations

import asyncio

from app.schemas.agent_state import ParsedRequirements
from app.schemas.buyer_context import BuyerContext
from app.schemas.user_profile import UserSourcingProfile

from .aggregator import AggregatedDiscoveryResults, aggregate_team_results
from .strategy_selector import DiscoveryTeam, TeamConfig, select_strategies
from .team_direct_manufacturer import run_direct_manufacturer_search
from .team_market_intelligence import run_market_intelligence_sweep
from .team_proximity_logistics import run_proximity_logistics_search
from .team_regional_deep_dive import run_regional_deep_dive
from .team_reputation_trust import run_reputation_trust_search


async def _run_team(
    team_config: TeamConfig,
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
    user_profile: UserSourcingProfile | None,
):
    if team_config.team == DiscoveryTeam.DIRECT_MANUFACTURER:
        return await run_direct_manufacturer_search(requirements, buyer_context)
    if team_config.team == DiscoveryTeam.MARKET_INTELLIGENCE:
        return await run_market_intelligence_sweep(requirements, buyer_context)
    if team_config.team == DiscoveryTeam.REGIONAL_DEEP_DIVE:
        return await run_regional_deep_dive(requirements, buyer_context, requirements.regional_searches)
    if team_config.team == DiscoveryTeam.REPUTATION_TRUST:
        return await run_reputation_trust_search(requirements, buyer_context, user_profile)
    return await run_proximity_logistics_search(requirements, buyer_context)


async def discover_suppliers(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext | None = None,
    user_profile: UserSourcingProfile | None = None,
) -> AggregatedDiscoveryResults:
    """Coordinate multi-team discovery and aggregation."""
    context = buyer_context or BuyerContext()
    teams = await select_strategies(requirements, context, user_profile)

    team_results = await asyncio.gather(
        *[_run_team(team, requirements, context, user_profile) for team in teams],
        return_exceptions=True,
    )

    clean_results = [result for result in team_results if not isinstance(result, Exception)]
    return await aggregate_team_results(clean_results, requirements, context)
