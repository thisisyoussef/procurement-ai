"""Discovery strategy selection for multi-team discovery."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.agent_state import ParsedRequirements
from app.schemas.buyer_context import BuyerContext
from app.schemas.user_profile import UserSourcingProfile


class DiscoveryTeam(str, Enum):
    DIRECT_MANUFACTURER = "direct_manufacturer"
    MARKET_INTELLIGENCE = "market_intelligence"
    REGIONAL_DEEP_DIVE = "regional_deep_dive"
    REPUTATION_TRUST = "reputation_trust"
    PROXIMITY_LOGISTICS = "proximity_logistics"


class TeamConfig(BaseModel):
    team: DiscoveryTeam
    priority: int
    search_queries: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    max_results: int = 20
    scoring_lens: str = "balanced"


def _priority_tradeoff(requirements: ParsedRequirements, buyer_context: BuyerContext) -> str:
    return (
        requirements.priority_tradeoff
        or buyer_context.priority_tradeoff
        or "balanced"
    )


async def select_strategies(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
    user_profile: UserSourcingProfile | None = None,
) -> list[TeamConfig]:
    """Select 2-5 discovery teams based on requirements and buyer context."""
    teams: list[TeamConfig] = [
        TeamConfig(
            team=DiscoveryTeam.DIRECT_MANUFACTURER,
            priority=1,
            search_queries=requirements.search_queries,
            sources=["google_places", "firecrawl", "directories"],
            scoring_lens="manufacturing_confidence",
        ),
        TeamConfig(
            team=DiscoveryTeam.MARKET_INTELLIGENCE,
            priority=2,
            search_queries=requirements.search_queries,
            sources=["marketplaces", "trade_shows", "associations"],
            scoring_lens="market_position",
        ),
    ]

    has_regional = bool(requirements.regional_searches)
    has_import_experience = not bool(buyer_context.is_first_import)
    if has_regional and has_import_experience:
        teams.append(
            TeamConfig(
                team=DiscoveryTeam.REGIONAL_DEEP_DIVE,
                priority=3,
                search_queries=[q for q in requirements.search_queries[:4]],
                sources=["regional_search", "local_directories"],
                scoring_lens="regional_depth",
            )
        )

    profile_risk = (user_profile.risk_tolerance if user_profile else None) or "moderate"
    regulated_signals = {"medical", "food", "automotive", "battery", "electronic"}
    regulated_product = any(signal in (requirements.product_type or "").lower() for signal in regulated_signals)
    conservative = profile_risk in {"low", "conservative"} or buyer_context.is_first_import
    if conservative or regulated_product:
        teams.append(
            TeamConfig(
                team=DiscoveryTeam.REPUTATION_TRUST,
                priority=4,
                search_queries=requirements.search_queries,
                sources=["certification_dirs", "reviews", "supplier_memory"],
                scoring_lens="trust_level",
            )
        )

    tradeoff = _priority_tradeoff(requirements, buyer_context)
    deadline_urgent = bool(buyer_context.timeline.hard_deadline)
    if tradeoff == "fastest_delivery" or deadline_urgent:
        teams.append(
            TeamConfig(
                team=DiscoveryTeam.PROXIMITY_LOGISTICS,
                priority=5,
                search_queries=requirements.search_queries,
                sources=["domestic_dirs", "nearshore_dirs", "port_clusters"],
                scoring_lens="logistics_fit",
            )
        )

    teams.sort(key=lambda item: item.priority)
    return teams[:5]
