"""Reputation and trust-focused discovery team."""

from __future__ import annotations

from app.agents.supplier_discovery import discover_suppliers as legacy_discover_suppliers
from app.schemas.agent_state import ParsedRequirements
from app.schemas.buyer_context import BuyerContext
from app.schemas.user_profile import UserSourcingProfile

from .aggregator import TeamResult
from .strategy_selector import DiscoveryTeam


def _known_supplier_bias(name: str, profile: UserSourcingProfile | None) -> float:
    if not profile:
        return 0.0
    low_name = name.lower()
    for relation in profile.supplier_relationships:
        if relation.supplier_name.lower() != low_name:
            continue
        if relation.sentiment == "positive":
            return 20.0
        if relation.sentiment == "negative":
            return -20.0
    return 0.0


async def run_reputation_trust_search(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
    user_profile: UserSourcingProfile | None = None,
) -> TeamResult:
    tuned = requirements.model_copy(deep=True)
    product = requirements.product_type or "product"
    tuned.search_queries = list(dict.fromkeys(
        [
            f"{product} certified supplier",
            f"{product} ISO supplier reviews",
            f"{product} trusted exporter",
            *(requirements.search_queries or []),
        ]
    ))

    results = await legacy_discover_suppliers(tuned, buyer_context=buyer_context, user_profile=user_profile)
    for supplier in results.suppliers:
        supplier.discovery_teams = sorted({*(supplier.discovery_teams or []), DiscoveryTeam.REPUTATION_TRUST.value})
        rating_component = (supplier.google_rating or 0.0) * 15.0
        review_component = min(20.0, float(supplier.google_review_count or 0) / 8.0)
        cert_component = min(25.0, len(supplier.certifications or []) * 5.0)
        profile_bias = _known_supplier_bias(supplier.name, user_profile)
        supplier.trust_level = max(
            supplier.trust_level,
            max(0.0, min(100.0, rating_component + review_component + cert_component + profile_bias + 20.0)),
        )

    return TeamResult(
        team=DiscoveryTeam.REPUTATION_TRUST,
        suppliers=results.suppliers,
        coverage_notes="Trust and credibility lens",
        confidence=0.74,
    )
