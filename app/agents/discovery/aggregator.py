"""Aggregation layer for multi-team discovery outputs."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.schemas.agent_state import (
    DiscoveredSupplier,
    DiscoveryResults,
    MarketIntelligence,
    ParsedRequirements,
)
from app.schemas.buyer_context import BuyerContext
from .strategy_selector import DiscoveryTeam

TARGET_SURFACED_SUPPLIERS_MIN = 20


class TeamResult(BaseModel):
    """Output from a single discovery team."""

    team: DiscoveryTeam
    suppliers: list[DiscoveredSupplier] = Field(default_factory=list)
    market_intelligence: MarketIntelligence | None = None
    coverage_notes: str = ""
    confidence: float = 0.0


class AggregatedDiscoveryResults(DiscoveryResults):
    """Enhanced DiscoveryResults with multi-team data."""

    team_reports: list[TeamResult] = Field(default_factory=list)
    cross_reference_boost: dict[str, float] = Field(default_factory=dict)
    coverage_gaps: list[str] = Field(default_factory=list)


def _supplier_key(supplier: DiscoveredSupplier) -> str:
    if supplier.website:
        candidate = supplier.website.strip().lower()
        if "://" not in candidate:
            candidate = f"https://{candidate}"
        try:
            host = urlparse(candidate).netloc
            if host.startswith("www."):
                host = host[4:]
            if host:
                return f"domain:{host}"
        except Exception:  # noqa: BLE001
            pass
    if supplier.email:
        return f"email:{supplier.email.strip().lower()}"
    return f"name:{supplier.name.strip().lower()}"


def _merge(existing: DiscoveredSupplier, incoming: DiscoveredSupplier) -> DiscoveredSupplier:
    if incoming.email and not existing.email:
        existing.email = incoming.email
    if incoming.phone and not existing.phone:
        existing.phone = incoming.phone
    if incoming.website and not existing.website:
        existing.website = incoming.website
    if incoming.country and not existing.country:
        existing.country = incoming.country
    if incoming.description and (not existing.description or len(incoming.description) > len(existing.description)):
        existing.description = incoming.description

    existing.certifications = sorted({*(existing.certifications or []), *(incoming.certifications or [])})
    existing.categories = sorted({*(existing.categories or []), *(incoming.categories or [])})

    existing.manufacturing_confidence = max(existing.manufacturing_confidence, incoming.manufacturing_confidence)
    existing.market_position = max(existing.market_position, incoming.market_position)
    existing.regional_depth_score = max(existing.regional_depth_score, incoming.regional_depth_score)
    existing.trust_level = max(existing.trust_level, incoming.trust_level)
    existing.logistics_fit = max(existing.logistics_fit, incoming.logistics_fit)

    existing.discovery_teams = sorted({*(existing.discovery_teams or []), *(incoming.discovery_teams or [])})
    existing.cross_reference_count = len(existing.discovery_teams)
    existing.relevance_score = max(existing.relevance_score, incoming.relevance_score)
    return existing


def _weighted_score(supplier: DiscoveredSupplier, buyer_context: BuyerContext) -> float:
    tradeoff = buyer_context.priority_tradeoff or "balanced"
    base = {
        "manufacturing": supplier.manufacturing_confidence,
        "market": supplier.market_position,
        "regional": supplier.regional_depth_score,
        "trust": supplier.trust_level,
        "logistics": supplier.logistics_fit,
    }

    if tradeoff == "lowest_cost":
        weights = {"manufacturing": 0.2, "market": 0.35, "regional": 0.1, "trust": 0.2, "logistics": 0.15}
    elif tradeoff == "fastest_delivery":
        weights = {"manufacturing": 0.2, "market": 0.15, "regional": 0.1, "trust": 0.2, "logistics": 0.35}
    elif tradeoff == "highest_quality":
        weights = {"manufacturing": 0.3, "market": 0.1, "regional": 0.1, "trust": 0.35, "logistics": 0.15}
    else:
        weights = {"manufacturing": 0.25, "market": 0.2, "regional": 0.15, "trust": 0.25, "logistics": 0.15}

    return sum(base[key] * weight for key, weight in weights.items())


async def haiku_relevance_filter(
    suppliers: list[DiscoveredSupplier],
    requirements: ParsedRequirements,
) -> list[DiscoveredSupplier]:
    """Lightweight relevance filter before expensive scoring.

    Fallback implementation uses lexical filtering when tool-use is disabled.
    """
    anchors = [token for token in (requirements.product_type or "").lower().split() if len(token) > 2]
    if not anchors:
        return suppliers

    filtered: list[DiscoveredSupplier] = []
    for supplier in suppliers:
        haystack = " ".join(
            [
                supplier.name or "",
                supplier.description or "",
                " ".join(supplier.categories or []),
            ]
        ).lower()
        if any(anchor in haystack for anchor in anchors):
            filtered.append(supplier)
    return filtered or suppliers


async def aggregate_team_results(
    team_results: list[TeamResult],
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> AggregatedDiscoveryResults:
    """Merge results from all teams into a single ranked list."""
    merged: dict[str, DiscoveredSupplier] = {}
    references: Counter[str] = Counter()

    sources: set[str] = set()
    market_intelligence: MarketIntelligence | None = None

    for team in team_results:
        sources.add(team.team.value)
        if team.market_intelligence and market_intelligence is None:
            market_intelligence = team.market_intelligence
        for supplier in team.suppliers:
            supplier.discovery_teams = sorted({*(supplier.discovery_teams or []), team.team.value})
            key = _supplier_key(supplier)
            references[key] += 1
            if key in merged:
                merged[key] = _merge(merged[key], supplier)
            else:
                supplier.cross_reference_count = len(supplier.discovery_teams)
                merged[key] = supplier

    suppliers = list(merged.values())
    pre_filter_suppliers = list(suppliers)
    suppliers = await haiku_relevance_filter(suppliers, requirements)

    if len(suppliers) < TARGET_SURFACED_SUPPLIERS_MIN and pre_filter_suppliers:
        existing_keys = {_supplier_key(s) for s in suppliers}
        backfill_candidates = [
            s for s in sorted(pre_filter_suppliers, key=lambda item: item.relevance_score, reverse=True)
            if _supplier_key(s) not in existing_keys
        ]
        needed = TARGET_SURFACED_SUPPLIERS_MIN - len(suppliers)
        suppliers.extend(backfill_candidates[:needed])

    cross_reference_boost: dict[str, float] = {}
    for supplier in suppliers:
        key = _supplier_key(supplier)
        ref_count = references.get(key, 1)
        supplier.cross_reference_count = ref_count

        if ref_count >= 4:
            boost = 35.0
        elif ref_count == 3:
            boost = 25.0
        elif ref_count == 2:
            boost = 15.0
        else:
            boost = 0.0

        score = _weighted_score(supplier, buyer_context)
        supplier.relevance_score = min(100.0, score + boost)
        cross_reference_boost[supplier.name] = boost

    suppliers.sort(key=lambda item: item.relevance_score, reverse=True)

    coverage_gaps: list[str] = []
    if not any(s.trust_level >= 60 for s in suppliers):
        coverage_gaps.append("No strongly trusted suppliers identified")
    if not any((s.country or "").lower() in {"united states", "usa", "us", "mexico", "canada"} for s in suppliers):
        coverage_gaps.append("No domestic or nearshore options detected")
    if not suppliers:
        coverage_gaps.append("No suppliers passed relevance filter")

    return AggregatedDiscoveryResults(
        suppliers=suppliers,
        market_intelligence=market_intelligence,
        team_reports=team_results,
        cross_reference_boost=cross_reference_boost,
        coverage_gaps=coverage_gaps,
        sources_searched=sorted(sources),
        total_raw_results=sum(len(t.suppliers) for t in team_results),
        deduplicated_count=len(suppliers),
    )
