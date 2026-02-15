"""Agent 2 — Supplier Discovery.

Searches multiple data sources in parallel to build a comprehensive
longlist of potential suppliers matching the parsed requirements.
Uses Sonnet for intelligent search strategy and result merging.
"""

import asyncio
import logging
import uuid
from typing import Any

from automotive.core.config import MODEL_TIER_BALANCED
from automotive.core.llm import call_llm_structured
from automotive.schemas.discovery import DiscoveredSupplier, DiscoveryResult
from automotive.schemas.requirements import ParsedRequirement
from automotive.tools.google_places import search_google_places
from automotive.tools.firecrawl_search import search_web_firecrawl
from automotive.tools.thomasnet import search_thomasnet

logger = logging.getLogger(__name__)

RANKING_SYSTEM_PROMPT = """\
You are Tamkin's Supplier Ranking Agent for automotive procurement.
Given a list of raw supplier search results and the procurement requirement,
score and rank each supplier.

Scoring dimensions (each 0–100):
- capability_match: How well do the supplier's known processes/materials match?
- certification_match: 100 if IATF 16949 confirmed, 50 if ISO 9001 or unknown, 0 if known absent
- geographic_fit: 100 if in preferred region, scaled by distance/USMCA compliance
- scale_fit: Does employee count/revenue suggest capacity for this volume?
- data_richness: How much information was found? More sources = higher confidence

Composite = 0.25×capability + 0.25×cert + 0.20×geo + 0.15×scale + 0.15×richness

Prioritize RECALL — include marginally relevant suppliers rather than miss good ones.
The Qualification Agent will filter later.
"""


def _build_search_queries(req: ParsedRequirement) -> list[dict]:
    """Build search queries for each data source based on the requirement."""
    queries = []
    base_terms = f"{req.manufacturing_process} {req.material_family}"
    category_terms = req.part_category.replace("_", " ")

    # Google Places queries
    for region in req.preferred_regions or ["United States", "Mexico"]:
        queries.append({
            "source": "google_places",
            "query": f"{category_terms} manufacturer {region}",
            "region": region,
        })
        queries.append({
            "source": "google_places",
            "query": f"{base_terms} automotive supplier {region}",
            "region": region,
        })

    # Web search queries
    cert_filter = "IATF 16949" if "IATF 16949" in req.certifications_required else ""
    queries.append({
        "source": "web",
        "query": f"{base_terms} automotive supplier {cert_filter}".strip(),
    })
    queries.append({
        "source": "web",
        "query": f"{category_terms} manufacturer automotive tier 2 {' '.join(req.preferred_regions)}",
    })

    # Thomasnet queries
    queries.append({
        "source": "thomasnet",
        "query": f"{category_terms} {req.material_family}",
    })

    return queries


def _deduplicate_suppliers(suppliers: list[DiscoveredSupplier]) -> list[DiscoveredSupplier]:
    """Merge duplicate suppliers found across multiple sources."""
    seen: dict[str, DiscoveredSupplier] = {}

    for s in suppliers:
        # Normalize name for matching
        norm_name = s.company_name.lower().strip()
        for suffix in [" inc", " inc.", " llc", " ltd", " corp", " corp.", " s.a.", " sa de cv", " s de rl"]:
            norm_name = norm_name.replace(suffix, "")
        norm_name = norm_name.strip()

        if norm_name in seen:
            # Merge: combine sources, keep best data
            existing = seen[norm_name]
            existing.sources = list(set(existing.sources + s.sources))
            if not existing.website and s.website:
                existing.website = s.website
            if not existing.phone and s.phone:
                existing.phone = s.phone
            if not existing.email and s.email:
                existing.email = s.email
            existing.known_processes = list(set(existing.known_processes + s.known_processes))
            existing.known_materials = list(set(existing.known_materials + s.known_materials))
            existing.known_certifications = list(set(existing.known_certifications + s.known_certifications))
            existing.data_richness = min(100, existing.data_richness + 15)
        else:
            seen[norm_name] = s

    return list(seen.values())


async def discover_suppliers(requirement: ParsedRequirement) -> DiscoveryResult:
    """Run parallel discovery across all data sources."""
    logger.info("Starting discovery for: %s %s", requirement.part_category, requirement.material_family)
    queries = _build_search_queries(requirement)
    all_suppliers: list[DiscoveredSupplier] = []
    sources_searched: list[str] = []
    search_queries_used: list[str] = []

    # Run searches in parallel by source type
    google_tasks = []
    web_tasks = []
    thomasnet_tasks = []

    for q in queries:
        search_queries_used.append(f"[{q['source']}] {q['query']}")
        if q["source"] == "google_places":
            google_tasks.append(search_google_places(q["query"]))
        elif q["source"] == "web":
            web_tasks.append(search_web_firecrawl(q["query"]))
        elif q["source"] == "thomasnet":
            thomasnet_tasks.append(search_thomasnet(q["query"]))

    # Execute all searches concurrently
    results = await asyncio.gather(
        *google_tasks, *web_tasks, *thomasnet_tasks,
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            logger.warning("Search failed: %s", result)
            continue
        if isinstance(result, list):
            all_suppliers.extend(result)
            if result:
                sources_searched.append(result[0].sources[0] if result[0].sources else "unknown")

    # Deduplicate
    unique_suppliers = _deduplicate_suppliers(all_suppliers)

    # Assign IDs to any that don't have one
    for s in unique_suppliers:
        if not s.supplier_id:
            s.supplier_id = str(uuid.uuid4())

    # Use LLM to rank if we have enough suppliers
    if len(unique_suppliers) > 3:
        unique_suppliers = await _llm_rank_suppliers(unique_suppliers, requirement)

    # Sort by score descending
    unique_suppliers.sort(key=lambda s: s.initial_score, reverse=True)

    logger.info("Discovery complete: %d unique suppliers from %d sources", len(unique_suppliers), len(set(sources_searched)))

    return DiscoveryResult(
        total_found=len(unique_suppliers),
        sources_searched=list(set(sources_searched)),
        suppliers=unique_suppliers,
        search_queries_used=search_queries_used,
        gaps_identified=_identify_gaps(unique_suppliers, requirement),
    )


async def _llm_rank_suppliers(
    suppliers: list[DiscoveredSupplier],
    requirement: ParsedRequirement,
) -> list[DiscoveredSupplier]:
    """Use Sonnet to score and rank discovered suppliers."""
    supplier_summaries = []
    for s in suppliers[:50]:  # Cap at 50 to fit context
        supplier_summaries.append(
            f"- {s.company_name} | {s.headquarters} | Processes: {', '.join(s.known_processes)} | "
            f"Materials: {', '.join(s.known_materials)} | Certs: {', '.join(s.known_certifications)} | "
            f"Employees: {s.employee_count or 'unknown'} | Revenue: {s.estimated_revenue or 'unknown'} | "
            f"Sources: {', '.join(s.sources)}"
        )

    schema = {
        "type": "object",
        "properties": {
            "rankings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "capability_match": {"type": "number"},
                        "certification_match": {"type": "number"},
                        "geographic_fit": {"type": "number"},
                        "scale_fit": {"type": "number"},
                        "data_richness": {"type": "number"},
                    },
                    "required": ["company_name", "capability_match", "certification_match",
                                 "geographic_fit", "scale_fit", "data_richness"],
                },
            }
        },
        "required": ["rankings"],
    }

    user_msg = (
        f"Requirement: {requirement.part_description}\n"
        f"Category: {requirement.part_category}\n"
        f"Material: {requirement.material_family} ({requirement.material_spec or 'unspecified'})\n"
        f"Volume: {requirement.annual_volume}/year\n"
        f"Certifications: {', '.join(requirement.certifications_required)}\n"
        f"Regions: {', '.join(requirement.preferred_regions)}\n"
        f"Buyer location: {requirement.buyer_plant_location or 'unspecified'}\n\n"
        f"Suppliers found:\n" + "\n".join(supplier_summaries)
    )

    try:
        result = await call_llm_structured(
            system=RANKING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            output_schema=schema,
            model=MODEL_TIER_BALANCED,
            max_tokens=4096,
        )

        # Apply scores back to suppliers
        name_to_scores = {r["company_name"].lower().strip(): r for r in result.get("rankings", [])}
        for s in suppliers:
            scores = name_to_scores.get(s.company_name.lower().strip())
            if scores:
                s.capability_match = scores.get("capability_match", 0)
                s.certification_match = scores.get("certification_match", 0)
                s.geographic_fit = scores.get("geographic_fit", 0)
                s.scale_fit = scores.get("scale_fit", 0)
                s.data_richness = scores.get("data_richness", 0)
                s.initial_score = (
                    0.25 * s.capability_match
                    + 0.25 * s.certification_match
                    + 0.20 * s.geographic_fit
                    + 0.15 * s.scale_fit
                    + 0.15 * s.data_richness
                )
    except Exception:
        logger.exception("LLM ranking failed, using source-count heuristic")
        for s in suppliers:
            s.initial_score = len(s.sources) * 20 + s.data_richness

    return suppliers


def _identify_gaps(suppliers: list[DiscoveredSupplier], req: ParsedRequirement) -> list[str]:
    """Identify coverage gaps in the discovery results."""
    gaps = []
    if len(suppliers) < 5:
        gaps.append(f"Low supplier count ({len(suppliers)}). Consider broadening search criteria.")
    regions_found = set()
    for s in suppliers:
        regions_found.add(s.headquarters.split(",")[-1].strip() if s.headquarters else "")
    for region in req.preferred_regions:
        if not any(region.lower() in r.lower() for r in regions_found):
            gaps.append(f"No suppliers found in preferred region: {region}")
    if not any(s.known_certifications for s in suppliers):
        gaps.append("No certification data found for any supplier. IATF verification will be critical.")
    return gaps


async def run(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point."""
    req_data = state.get("parsed_requirement")
    if not req_data:
        return {"errors": [{"stage": "discover", "error": "No parsed_requirement in state"}]}

    requirement = ParsedRequirement(**req_data)
    result = await discover_suppliers(requirement)

    return {
        "discovery_result": result.model_dump(),
        "current_stage": "discover",
        "messages": [
            {
                "role": "system",
                "content": f"Discovery complete: {result.total_found} suppliers found across {', '.join(result.sources_searched)}",
            }
        ],
    }
