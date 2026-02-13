"""Agent B: Supplier Discovery — searches multiple sources in parallel.

Enhanced with:
- Multi-language regional search (Chinese, Turkish, Vietnamese, etc.)
- Intermediary/directory site detection and direct manufacturer resolution
- Iterative search expansion when initial results are insufficient
"""

import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.core.progress import emit_progress
from app.agents.tools.google_places import search_google_places
from app.agents.tools.firecrawl_scraper import search_web
from app.agents.tools.intermediary_resolver import (
    detect_intermediary_by_url,
    classify_intermediary_by_content,
    resolve_direct_website,
    extract_manufacturers_from_listing,
)
from app.schemas.agent_state import (
    DiscoveredSupplier,
    DiscoveryResults,
    IntermediaryDetection,
    ParsedRequirements,
    RegionalSearchConfig,
)
from app.services.supplier_memory import search_supplier_memory_candidates

settings = get_settings()
logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "discovery.md").read_text()


# ── Marketplace Constants ────────────────────────────────────────

COMMON_MARKETPLACES = [
    {"name": "etsy", "domain": "etsy.com", "suffix": ""},
    {"name": "alibaba", "domain": "alibaba.com", "suffix": "manufacturer"},
    {"name": "amazon", "domain": "amazon.com", "suffix": ""},
]
B2B_MARKETPLACES = [
    {"name": "thomasnet", "domain": "thomasnet.com", "suffix": "", "tags": ["industrial", "machinery", "components", "electronics", "packaging"]},
    {"name": "indiamart", "domain": "indiamart.com", "suffix": "", "tags": ["textiles", "apparel", "jewelry", "handicrafts", "chemicals"]},
    {"name": "faire", "domain": "faire.com", "suffix": "", "tags": ["home decor", "candles", "jewelry", "food", "beauty", "apparel"]},
    {"name": "globalsources", "domain": "globalsources.com", "suffix": "", "tags": ["electronics", "hardware", "packaging", "machinery"]},
    {"name": "europages", "domain": "europages.com", "suffix": "", "tags": ["industrial", "food", "textiles", "chemicals"]},
    {"name": "made_in_china", "domain": "made-in-china.com", "suffix": "manufacturer", "tags": ["electronics", "toys", "packaging", "textiles", "hardware"]},
]

INDUSTRIAL_MARKETPLACE_NAMES = {
    "alibaba",
    "thomasnet",
    "globalsources",
    "europages",
    "made_in_china",
    "indiamart",
}

INDUSTRIAL_SIGNALS = {
    "automotive",
    "oem",
    "tier 1",
    "tier-1",
    "tier 2",
    "tier-2",
    "iatf",
    "ppap",
    "apqp",
    "stamped steel",
    "stamping",
    "seat bracket",
    "wire harness",
    "machining",
    "forging",
    "drivetrain",
    "inverter",
    "die cast",
    "gm",
}

CONSUMER_MERCH_INDICATORS = {
    "tote",
    "hoodie",
    "hoodies",
    "streetwear",
    "apparel",
    "merch",
    "gift shop",
    "boutique",
    "canvas bag",
    "promotional bag",
    "e-commerce store",
}


def _select_b2b_marketplaces(product_type: str, max_count: int = 3) -> list[dict]:
    """Pick the most relevant B2B marketplaces for the product type."""
    product_lower = product_type.lower()
    scored = []
    for mp in B2B_MARKETPLACES:
        score = sum(2 if kw in product_lower or product_lower in kw else
                    1 if any(w in kw for w in product_lower.split()) else 0
                    for kw in mp["tags"])
        scored.append((score, mp))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [mp for _, mp in scored[:max_count]]


def _is_industrial_oem_requirements(requirements: ParsedRequirements) -> bool:
    blob = " ".join(
        [
            requirements.product_type or "",
            requirements.material or "",
            requirements.customization or "",
            requirements.sourcing_strategy or "",
            " ".join(requirements.certifications_needed or []),
            " ".join(requirements.search_queries or []),
        ]
    ).lower()
    return any(signal in blob for signal in INDUSTRIAL_SIGNALS)


# ── Product Page URL Validation ──────────────────────────────────

def _validate_product_page_url(product_url: str | None, website: str | None) -> str | None:
    """Only keep product_page_url if it's a real product page, not hallucinated."""
    if not product_url:
        return None
    product_url = product_url.strip()
    # If same as website, not a product page
    if website and product_url.rstrip("/") == website.strip().rstrip("/"):
        return None
    from urllib.parse import urlparse
    try:
        parsed = urlparse(product_url if "://" in product_url else f"https://{product_url}")
        path = parsed.path.strip("/")
        if not path:
            return None
        # Marketplace patterns — always valid
        marketplace_patterns = [
            "etsy.com/listing/", "alibaba.com/product-detail/",
            "amazon.com/dp/", "amazon.com/gp/product/",
            "indiamart.com/proddetail/", "faire.com/product/",
            "globalsources.com/product/", "made-in-china.com/product-detail/",
        ]
        url_lower = product_url.lower()
        if any(p in url_lower for p in marketplace_patterns):
            return product_url
        # Product-like path indicators
        product_indicators = ["/product", "/listing", "/item", "/shop/", "/p/", "/dp/", "/catalog", "/collection", "/detail"]
        path_lower = f"/{path.lower()}"
        if any(ind in path_lower for ind in product_indicators):
            return product_url
        # Deep path (2+ segments) = likely a product page
        if len([s for s in path.split("/") if s]) >= 2:
            return product_url
        return None
    except Exception:
        return None


# ── Search Functions ─────────────────────────────────────────────

async def _search_google(queries: list[str], max_per_query: int = 5, location_hint: str | None = None) -> list[dict]:
    """Run multiple Google Places searches in parallel."""
    logger.info("🔍 Searching Google Places with %d queries...", len(queries[:3]))
    emit_progress("discovering", "searching_google",
                  f"Searching Google Places with {len(queries[:3])} queries...")
    tasks = [search_google_places(q, location_bias=location_hint, max_results=max_per_query) for q in queries[:3]]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)
    all_results = []
    for r in results_lists:
        if isinstance(r, list):
            all_results.extend(r)
    logger.info("Google Places returned %d results", len(all_results))
    return all_results


async def _search_web(queries: list[str], max_per_query: int = 3) -> list[dict]:
    """Run Firecrawl web searches for supplier directories."""
    logger.info("🔍 Searching web via Firecrawl with %d queries...", len(queries[:2]))
    emit_progress("discovering", "searching_web",
                  f"Searching web directories with {len(queries[:2])} queries...")
    # Add "supplier" and "manufacturer" modifiers
    modified = [f"{q} factory manufacturer wholesale" for q in queries[:2]]
    tasks = [search_web(q, max_results=max_per_query) for q in modified]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)
    all_results = []
    for r in results_lists:
        if isinstance(r, list):
            all_results.extend(r)
    logger.info("Firecrawl web search returned %d results", len(all_results))
    return all_results


async def _search_marketplaces(
    product_type: str,
    material: str | None = None,
    industrial_mode: bool = False,
    max_per_query: int = 3,
) -> list[dict]:
    """Search Etsy, Alibaba, Amazon, and B2B marketplaces via Firecrawl site: queries."""
    search_term = f"{material} {product_type}" if material else product_type
    selected_b2b = _select_b2b_marketplaces(product_type, max_count=4)
    if industrial_mode:
        all_mps = [
            mp for mp in (COMMON_MARKETPLACES + selected_b2b)
            if mp["name"] in INDUSTRIAL_MARKETPLACE_NAMES
        ]
    else:
        all_mps = COMMON_MARKETPLACES + selected_b2b

    logger.info("🏪 Searching %d marketplaces for '%s'...", len(all_mps), search_term)
    emit_progress("discovering", "searching_marketplaces",
                  f"Searching {len(all_mps)} marketplaces: {', '.join(m['name'] for m in all_mps)}...")

    tasks, mp_names = [], []
    for mp in all_mps:
        suffix = f" {mp['suffix']}" if mp.get("suffix") else ""
        tasks.append(search_web(f"site:{mp['domain']} {search_term}{suffix}", max_results=max_per_query))
        mp_names.append(mp["name"])

    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for i, r in enumerate(results_lists):
        if isinstance(r, list):
            for result in r:
                result["source"] = f"marketplace_{mp_names[i]}"
                result["marketplace"] = mp_names[i]
                result["is_product_listing"] = True
            all_results.extend(r)

    logger.info("🏪 Marketplace searches returned %d results", len(all_results))
    return all_results


async def _search_regional(
    regional_configs: list[RegionalSearchConfig],
    max_per_query: int = 3,
) -> list[dict]:
    """Run regional searches in multiple languages in parallel.

    For each region, searches Google Places (with language_code) and Firecrawl web search.
    Tags each result with language_discovered and region metadata.
    """
    if not regional_configs:
        return []

    logger.info("🌍 Running regional searches across %d regions...", len(regional_configs))
    all_tasks = []
    task_metadata = []  # Track which region each task belongs to

    for config in regional_configs:
        emit_progress("discovering", "searching_regional",
                      f"Searching in {config.language_name} for {config.region}-based manufacturers...")
        for query in config.search_queries[:2]:
            # Google Places with regional language
            all_tasks.append(search_google_places(
                query, max_results=max_per_query, language_code=config.language_code
            ))
            task_metadata.append(("google_places_regional", config))

            # Firecrawl web search (handles multilingual natively)
            all_tasks.append(search_web(query, max_results=max_per_query))
            task_metadata.append(("firecrawl_regional", config))

    results_lists = await asyncio.gather(*all_tasks, return_exceptions=True)

    all_results = []
    for i, r in enumerate(results_lists):
        if isinstance(r, list):
            config = task_metadata[i][1]
            for result in r:
                result["language_discovered"] = config.language_code
                result["region"] = config.region
                result["source"] = f"{task_metadata[i][0]}_{config.region.lower()}"
            all_results.extend(r)

    logger.info("🌍 Regional searches returned %d results", len(all_results))
    return all_results


async def _search_supplier_memory(requirements: ParsedRequirements, max_results: int = 20) -> list[DiscoveredSupplier]:
    """Query internal supplier memory so discovery is hybrid, not web-only."""
    emit_progress("discovering", "searching_supplier_memory", "Searching Tamkin supplier memory...")
    return await search_supplier_memory_candidates(requirements, limit=max_results)


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
    if supplier.supplier_id:
        return f"id:{supplier.supplier_id}"
    country = (supplier.country or "").strip().lower()
    return f"name:{supplier.name.strip().lower()}|country:{country}"


def _merge_supplier(existing: DiscoveredSupplier, incoming: DiscoveredSupplier) -> DiscoveredSupplier:
    if incoming.supplier_id and not existing.supplier_id:
        existing.supplier_id = incoming.supplier_id

    if incoming.website and not existing.website:
        existing.website = incoming.website
    if incoming.product_page_url and not existing.product_page_url:
        existing.product_page_url = incoming.product_page_url
    if incoming.email and not existing.email:
        existing.email = incoming.email
    if incoming.phone and not existing.phone:
        existing.phone = incoming.phone
    if incoming.address and not existing.address:
        existing.address = incoming.address
    if incoming.city and not existing.city:
        existing.city = incoming.city
    if incoming.country and not existing.country:
        existing.country = incoming.country
    if incoming.description and (not existing.description or len(incoming.description) > len(existing.description)):
        existing.description = incoming.description
    if incoming.estimated_shipping_cost and not existing.estimated_shipping_cost:
        existing.estimated_shipping_cost = incoming.estimated_shipping_cost
    if incoming.google_rating is not None and (existing.google_rating is None or incoming.google_rating > existing.google_rating):
        existing.google_rating = incoming.google_rating
    if incoming.google_review_count is not None and (
        existing.google_review_count is None or incoming.google_review_count > existing.google_review_count
    ):
        existing.google_review_count = incoming.google_review_count
    if incoming.language_discovered and not existing.language_discovered:
        existing.language_discovered = incoming.language_discovered

    existing.categories = sorted({*(existing.categories or []), *(incoming.categories or [])})
    existing.certifications = sorted({*(existing.certifications or []), *(incoming.certifications or [])})

    if incoming.source == "supplier_memory" and existing.source != "supplier_memory":
        existing.source = f"{existing.source}+supplier_memory"
        existing.relevance_score = min(100.0, max(existing.relevance_score, incoming.relevance_score) + 4.0)
    elif existing.source == "supplier_memory" and incoming.source != "supplier_memory":
        existing.source = f"{incoming.source}+supplier_memory"
        existing.relevance_score = min(100.0, max(existing.relevance_score, incoming.relevance_score) + 4.0)
    else:
        existing.relevance_score = max(existing.relevance_score, incoming.relevance_score)

    existing.raw_data = {
        **(existing.raw_data or {}),
        **(incoming.raw_data or {}),
        "hybrid_memory_match": existing.source.endswith("+supplier_memory") or existing.source == "supplier_memory",
    }
    return existing


def _merge_supplier_lists(
    primary: list[DiscoveredSupplier],
    extra: list[DiscoveredSupplier],
) -> list[DiscoveredSupplier]:
    merged: dict[str, DiscoveredSupplier] = {}
    for supplier in primary:
        merged[_supplier_key(supplier)] = supplier

    for supplier in extra:
        key = _supplier_key(supplier)
        if key in merged:
            merged[key] = _merge_supplier(merged[key], supplier)
        else:
            merged[key] = supplier

    return sorted(merged.values(), key=lambda s: s.relevance_score, reverse=True)


# ── Intermediary Detection & Resolution ──────────────────────────

async def _filter_and_resolve_intermediaries(
    suppliers: list[DiscoveredSupplier],
    requirements: ParsedRequirements,
) -> tuple[list[DiscoveredSupplier], int]:
    """Detect intermediary/directory sites and resolve to direct manufacturers.

    Two-tier detection:
    1. URL pattern matching (instant, free)
    2. LLM classification for ambiguous cases (Haiku, cheap)

    Returns:
        (updated_suppliers, intermediaries_resolved_count)
    """
    emit_progress("discovering", "checking_intermediaries",
                  f"Checking {len(suppliers)} suppliers for intermediary/directory sites...")

    resolved_count = 0
    updated = []

    for supplier in suppliers:
        # Skip intermediary detection for marketplace product listings
        if supplier.source and (
            supplier.source.startswith("marketplace_")
            or supplier.source == "supplier_memory"
            or supplier.source.endswith("+supplier_memory")
        ):
            updated.append(supplier)
            continue

        # Tier 1: URL pattern matching
        is_intermed, intermed_type = detect_intermediary_by_url(supplier.website)

        if is_intermed:
            logger.info("🔗 Intermediary detected (URL): %s (%s)", supplier.name, intermed_type)
            emit_progress("discovering", "resolving_intermediary",
                          f"Resolving manufacturer behind {intermed_type}: {supplier.name}...")

            # Try to resolve the direct manufacturer
            resolved = await _resolve_intermediary_supplier(
                supplier, requirements, intermed_type
            )
            if resolved:
                resolved_count += 1
                updated.append(resolved)
            else:
                # Keep but penalize
                supplier.is_intermediary = True
                supplier.intermediary_detection = IntermediaryDetection(
                    is_intermediary=True,
                    intermediary_type=intermed_type,
                    original_url=supplier.website,
                )
                supplier.relevance_score = max(0, supplier.relevance_score - 20)
                updated.append(supplier)
            continue

        # Tier 2: LLM check for ambiguous cases (only if LLM flagged it)
        if supplier.raw_data.get("suspected_intermediary"):
            detection = await classify_intermediary_by_content(
                supplier.name,
                supplier.description,
                supplier.website,
            )
            if detection.is_intermediary:
                logger.info("🔗 Intermediary detected (LLM): %s (%s)",
                           supplier.name, detection.intermediary_type)
                resolved = await _resolve_intermediary_supplier(
                    supplier, requirements, detection.intermediary_type
                )
                if resolved:
                    resolved_count += 1
                    updated.append(resolved)
                else:
                    supplier.is_intermediary = True
                    supplier.intermediary_detection = detection
                    supplier.relevance_score = max(0, supplier.relevance_score - 20)
                    updated.append(supplier)
                continue

        # Not an intermediary — keep as-is
        updated.append(supplier)

    if resolved_count > 0:
        emit_progress("discovering", "intermediaries_resolved",
                      f"Resolved {resolved_count} intermediary listings to direct manufacturers")

    return updated, resolved_count


async def _resolve_intermediary_supplier(
    supplier: DiscoveredSupplier,
    requirements: ParsedRequirements,
    intermed_type: str | None,
) -> DiscoveredSupplier | None:
    """Try to resolve an intermediary listing to a direct manufacturer."""
    # Try to extract manufacturer names from the listing
    description = supplier.description or ""
    raw_content = supplier.raw_data.get("content", description)

    if raw_content and len(raw_content) > 50:
        manufacturers = await extract_manufacturers_from_listing(
            raw_content, requirements.product_type
        )
    else:
        manufacturers = []

    # If we found a manufacturer name, search for their direct website
    if manufacturers:
        manufacturer_name = manufacturers[0]  # Take the best match
        direct_url = await resolve_direct_website(manufacturer_name, requirements.product_type)
        if direct_url:
            return DiscoveredSupplier(
                name=manufacturer_name,
                website=direct_url,
                email=supplier.email,
                phone=supplier.phone,
                city=supplier.city,
                country=supplier.country,
                description=f"Direct manufacturer (resolved from {supplier.name})",
                categories=supplier.categories,
                certifications=supplier.certifications,
                source=f"resolved_from_{supplier.source}",
                relevance_score=supplier.relevance_score,
                google_rating=supplier.google_rating,
                google_review_count=supplier.google_review_count,
                original_source_url=supplier.website,
                intermediary_detection=IntermediaryDetection(
                    is_intermediary=False,
                    intermediary_type=None,
                    original_url=supplier.website,
                    extracted_manufacturer_name=manufacturer_name,
                    resolved_direct_url=direct_url,
                ),
            )

    return None


# ── Iterative Search Expansion ───────────────────────────────────

def _should_expand_search(
    suppliers: list[DiscoveredSupplier],
    requirements: ParsedRequirements,
) -> tuple[bool, str]:
    """Decide if search results are insufficient and should be expanded.

    Returns:
        (should_expand, reason)
    """
    quality_suppliers = [s for s in suppliers if s.relevance_score >= 60 and not s.is_intermediary]

    if len(quality_suppliers) < 3:
        return True, "insufficient_results"
    if len(quality_suppliers) < 5 and len(suppliers) > 10:
        return True, "low_relevance"
    return False, ""


async def _generate_expansion_queries(
    requirements: ParsedRequirements,
    existing_results: list[DiscoveredSupplier],
    reason: str,
) -> list[str]:
    """Generate alternative search queries to expand the search.

    Uses Haiku for cheap query generation with strategic thinking.
    """
    existing_names = [s.name for s in existing_results[:10]]

    prompt = f"""The initial search for "{requirements.product_type}" found insufficient quality results.
Reason: {reason}

Existing queries that were used: {requirements.search_queries[:5]}
Suppliers already found: {existing_names}

Generate 3-5 NEW, DIFFERENT search queries to find more manufacturers. Think strategically:
- Use alternative product names or industry terms
- Try different geographic angles
- Search for industry associations or trade show exhibitors
- Use terms that factory owners would use, not consumers
- Think about adjacent product categories that the same factories might produce

Return a JSON array of query strings. Example: ["query1", "query2", "query3"]"""

    try:
        response = await call_llm_structured(
            prompt=prompt,
            system="Generate search queries for supplier discovery. Return a JSON array of strings.",
            model=settings.model_cheap,
            max_tokens=500,
        )
        text = response.strip().strip("`")
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        queries = json.loads(text)
        if isinstance(queries, list):
            return [q for q in queries if isinstance(q, str)][:5]
    except Exception as e:
        logger.warning("Failed to generate expansion queries: %s", e)

    # Fallback: generate simple variations
    return [
        f"{requirements.product_type} factory OEM",
        f"{requirements.product_type} manufacturer wholesale custom",
        f"custom {requirements.product_type} producer",
    ]


# ── LLM Scoring ─────────────────────────────────────────────────

async def _score_and_deduplicate(
    all_raw: list[dict],
    requirements: ParsedRequirements,
    industrial_mode: bool = False,
) -> list[DiscoveredSupplier]:
    """Send raw results to LLM for scoring, deduplication, and ranking."""
    emit_progress("discovering", "scoring",
                  f"AI analyzing and ranking {len(all_raw)} raw results...")

    industrial_guardrail = """

INDUSTRIAL/OEM GUARDRAIL:
- This request is industrial/OEM sourcing. Strongly penalize consumer merch and retail results.
- Tote bags, hoodies, streetwear, gift shops, boutiques, and generic e-commerce sellers should score below 20 unless they clearly manufacture the exact industrial part.
- Prefer suppliers mentioning OEM, manufacturing, factory, tooling, stamping, machining, APQP/PPAP/IATF readiness.
""" if industrial_mode else ""

    prompt = f"""Product requirements:
{requirements.model_dump_json(indent=2)}

Raw search results from multiple sources ({len(all_raw)} total):
{json.dumps(all_raw[:120], indent=2, default=str)[:30000]}

Analyze these results. Score each supplier on relevance to the product requirements.
Deduplicate suppliers that appear in multiple sources.
Flag intermediaries/directories with suspected_intermediary: true.
Normalize multilingual entries to English.
PRODUCT PAGE URL RULES:
- ONLY set product_page_url if the raw search data contains a URL that is clearly a product/listing page (URL path contains /product/, /listing/, /item/, /shop/, /dp/, etc.).
- If the only URL is a homepage (e.g., "https://example.com"), set product_page_url to null.
- If the source is "google_places", product_page_url MUST be null (Google only returns homepages).
- Marketplace result URLs (from "marketplace_*" sources) ARE real product pages — always use them.
- NEVER fabricate or guess URLs. If unsure, set product_page_url to null.

Include estimated_shipping_cost for international suppliers based on typical freight from their country.
Return ALL qualifying suppliers (relevance_score >= 20) as a JSON array — do NOT cap at an arbitrary number.

CRITICAL SCORING RULES:
1. PRODUCT TYPE is king — a supplier MUST make the actual product requested to score above 50. Material match alone is NOT enough.
   - "Egyptian cotton hoodies" → must be a HOODIE manufacturer. A pajama store using Egyptian cotton scores below 25.
   - "Italian leather bags" → must be a BAG manufacturer. A leather tannery alone scores below 35.
2. PENALIZE retail stores — shops, boutiques, e-commerce stores that sell to consumers (not B2B) get -30 to -40 points.
3. PRIORITIZE factories — actual manufacturers, factories, OEM producers get a +10-15 bonus.
4. Geographic material signals — if the product references a material origin (Egyptian cotton, Italian leather), prefer manufacturers FROM that region.
{industrial_guardrail}

MARKETPLACE RESULTS:
- Results with source starting with "marketplace_" come from real marketplace product listings (Etsy, Alibaba, Amazon, etc.).
- Their "url" field IS the product listing URL — use it as product_page_url.
- Do NOT flag marketplace product listings as suspected_intermediary.
- Preserve the source tag (e.g., "marketplace_etsy") in the output.

Each supplier object must have these fields:
name, website, product_page_url, email, phone, address, city, country, description, categories, certifications, source, relevance_score, estimated_shipping_cost, google_rating, google_review_count, suspected_intermediary, language_discovered

Return ONLY a JSON array. No explanation."""

    response_text = await call_llm_structured(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=8192,
    )

    # Parse response
    try:
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        supplier_data = json.loads(text)
        if isinstance(supplier_data, dict):
            supplier_data = supplier_data.get("suppliers", [])
    except (json.JSONDecodeError, KeyError):
        import re
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            supplier_data = json.loads(json_match.group())
        else:
            supplier_data = []

    suppliers = []
    for s in supplier_data:
        try:
            suppliers.append(DiscoveredSupplier(
                name=s.get("name", "Unknown"),
                website=s.get("website"),
                product_page_url=_validate_product_page_url(s.get("product_page_url"), s.get("website")),
                email=s.get("email"),
                phone=s.get("phone"),
                address=s.get("address"),
                city=s.get("city"),
                country=s.get("country"),
                description=s.get("description"),
                categories=s.get("categories", []),
                certifications=s.get("certifications", []),
                source=s.get("source", "unknown"),
                relevance_score=float(s.get("relevance_score", 0)),
                estimated_shipping_cost=s.get("estimated_shipping_cost"),
                google_rating=s.get("google_rating"),
                google_review_count=s.get("google_review_count"),
                raw_data=s,
                language_discovered=s.get("language_discovered"),
            ))
        except Exception as e:
            logger.warning("Failed to parse supplier entry: %s", str(e)[:100])
            continue

    return suppliers


# ── Main Discovery Function ─────────────────────────────────────

async def discover_suppliers(
    requirements: ParsedRequirements,
) -> DiscoveryResults:
    """
    Search multiple sources for suppliers matching requirements.

    Enhanced flow:
    1. Memory-first retrieval from internal supplier database
    2. Parallel English searches (Google Places + Firecrawl + marketplaces)
    3. Parallel regional/multilingual searches
    4. LLM scoring and deduplication
    5. Intermediary detection and resolution
    6. Iterative expansion if results are insufficient (max 2 rounds)
    """
    logger.info("🏭 Starting supplier discovery with %d search queries, %d regional configs",
                len(requirements.search_queries), len(requirements.regional_searches))
    industrial_mode = _is_industrial_oem_requirements(requirements)
    if industrial_mode:
        logger.info("🏭 Industrial/OEM mode enabled for discovery guardrails")
    queries = requirements.search_queries
    if not queries:
        queries = [f"{requirements.product_type} manufacturer"]

    # ── Step 1: Memory-first retrieval ────────────────────────
    sources_searched = []
    sources_failed = []
    memory_results: list[DiscoveredSupplier] = []

    try:
        memory_results = await _search_supplier_memory(requirements)
        sources_searched.append("supplier_memory")
        if memory_results:
            emit_progress(
                "discovering",
                "memory_candidates_loaded",
                f"Found {len(memory_results)} previously indexed supplier profiles in Tamkin memory.",
            )
    except Exception:  # noqa: BLE001
        logger.warning("Supplier memory lookup failed in discovery", exc_info=True)
        sources_failed.append("supplier_memory")
        memory_results = []

    # ── Step 2: Parallel English + Regional searches ──────────

    # Run live external searches after memory retrieval.
    search_tasks = [
        _search_google(queries, location_hint=requirements.delivery_location),
        _search_web(queries),
        _search_marketplaces(
            product_type=requirements.product_type,
            material=requirements.material,
            industrial_mode=industrial_mode,
        ),
    ]
    if requirements.regional_searches:
        search_tasks.append(_search_regional(requirements.regional_searches))

    results = await asyncio.gather(*search_tasks, return_exceptions=True)

    google_results = results[0]
    web_results = results[1]
    marketplace_results = results[2]
    regional_results = results[3] if len(results) > 3 else []

    all_raw = []

    if isinstance(google_results, list) and google_results:
        all_raw.extend(google_results)
        sources_searched.append("google_places")
    else:
        sources_failed.append("google_places")

    if isinstance(web_results, list) and web_results:
        all_raw.extend(web_results)
        sources_searched.append("firecrawl_web")
    else:
        sources_failed.append("firecrawl_web")

    if isinstance(marketplace_results, list) and marketplace_results:
        all_raw.extend(marketplace_results)
        sources_searched.append("marketplace_search")
    else:
        sources_failed.append("marketplace_search")

    # Track regional results
    regional_counts: dict[str, int] = {}
    if isinstance(regional_results, list) and regional_results:
        all_raw.extend(regional_results)
        sources_searched.append("regional_search")
        # Count by region
        for r in regional_results:
            region = r.get("region", "unknown")
            regional_counts[region] = regional_counts.get(region, 0) + 1

    logger.info("Raw results: %d total (%d Google, %d web, %d marketplace, %d regional, %d memory)",
                len(all_raw),
                len(google_results) if isinstance(google_results, list) else 0,
                len(web_results) if isinstance(web_results, list) else 0,
                len(marketplace_results) if isinstance(marketplace_results, list) else 0,
                len(regional_results) if isinstance(regional_results, list) else 0,
                len(memory_results))

    if not all_raw and not memory_results:
        logger.warning("⚠️ No raw or memory results from any source")
        return DiscoveryResults(
            suppliers=[],
            sources_searched=sources_searched,
            sources_failed=sources_failed,
            total_raw_results=0,
            deduplicated_count=0,
        )

    # ── Step 2: LLM scoring and deduplication ─────────────────
    if all_raw:
        emit_progress("discovering", "scoring", f"Found {len(all_raw)} raw results. AI is scoring and ranking...")
        suppliers = await _score_and_deduplicate(all_raw, requirements, industrial_mode=industrial_mode)
    else:
        suppliers = []

    if memory_results:
        suppliers = _merge_supplier_lists(suppliers, memory_results)
        emit_progress(
            "discovering",
            "merging_supplier_memory",
            f"Merged {len(memory_results)} supplier-memory candidates with live search results.",
        )

    # ── Step 3: Intermediary detection and resolution ─────────
    suppliers, intermediaries_resolved = await _filter_and_resolve_intermediaries(
        suppliers, requirements
    )

    # ── Step 4: Iterative expansion if needed ─────────────────
    search_rounds = 1
    expansion_reason = None

    for round_num in range(2):  # Max 2 expansion rounds
        should_expand, reason = _should_expand_search(suppliers, requirements)
        if not should_expand:
            break

        search_rounds += 1
        expansion_reason = reason
        logger.info("🔄 Search expansion round %d (reason: %s)", round_num + 2, reason)
        emit_progress("discovering", "expanding_search",
                      f"Round {round_num + 2}: Expanding search — {reason}. Finding more suppliers...")

        expansion_queries = await _generate_expansion_queries(
            requirements, suppliers, reason
        )

        # Run expansion searches (English + regional if available)
        exp_tasks = [
            _search_google(expansion_queries, max_per_query=5, location_hint=requirements.delivery_location),
            _search_web(expansion_queries, max_per_query=3),
        ]
        if requirements.regional_searches:
            exp_tasks.append(_search_regional(requirements.regional_searches, max_per_query=3))

        exp_results = await asyncio.gather(*exp_tasks, return_exceptions=True)

        new_raw = []
        for exp_r in exp_results:
            if isinstance(exp_r, list):
                new_raw.extend(exp_r)

        if new_raw:
            all_raw.extend(new_raw)
            # Re-score combined results
            suppliers = await _score_and_deduplicate(all_raw, requirements, industrial_mode=industrial_mode)
            if memory_results:
                suppliers = _merge_supplier_lists(suppliers, memory_results)
            suppliers, extra_resolved = await _filter_and_resolve_intermediaries(
                suppliers, requirements
            )
            intermediaries_resolved += extra_resolved

    # ── Step 5: Filter low-quality / irrelevant suppliers ─────
    RETAIL_INDICATORS = [
        "retail store", "retail-focused", "retail shop", "boutique",
        "e-commerce store", "online shop", "consumer store",
        "shopping mall", "department store", "gift shop",
        "appears to be retail", "sells to consumers",
    ]

    main_suppliers = []
    filtered_suppliers = []

    for s in suppliers:
        reason = None

        # Check low relevance
        if s.relevance_score < 30:
            reason = "low_relevance"
        # In industrial mode, remove consumer-merch results aggressively.
        elif industrial_mode:
            blob = " ".join(
                [
                    s.name or "",
                    s.description or "",
                    " ".join(s.categories or []),
                    s.source or "",
                ]
            ).lower()
            if any(ind in blob for ind in CONSUMER_MERCH_INDICATORS):
                reason = "wrong_industry"
            elif s.source in {"marketplace_etsy", "marketplace_amazon", "marketplace_faire"}:
                reason = "wrong_industry"
        # Check retail indicators at moderate relevance
        elif s.relevance_score < 50 and s.description:
            desc_lower = s.description.lower()
            if any(ind in desc_lower for ind in RETAIL_INDICATORS):
                reason = "retail_store"
        # Check wrong product type at low-moderate relevance
        elif s.relevance_score < 40 and s.description:
            desc_lower = s.description.lower()
            if "wrong product" in desc_lower or "does not manufacture" in desc_lower:
                reason = "wrong_product_type"

        if reason:
            s.filtered_reason = reason
            filtered_suppliers.append(s)
        else:
            main_suppliers.append(s)

    if filtered_suppliers:
        logger.info("🔍 Filtered %d suppliers: %s",
                    len(filtered_suppliers),
                    ", ".join(f"{s.name} ({s.filtered_reason})" for s in filtered_suppliers[:5]))
        emit_progress("discovering", "filtering",
                      f"Filtered {len(filtered_suppliers)} low-quality results (retail stores, irrelevant matches)")

    # ── Step 6: Lightweight contact enrichment for top suppliers ─
    # Run cheap enrichment (Tiers 1 & 2 only) for top suppliers missing
    # emails. This ensures the top-20 sent to verification already have
    # the best available contact info — suppliers without emails won't be
    # unfairly deprioritized or skipped during outreach.
    top_no_email = [
        s for s in sorted(main_suppliers, key=lambda x: x.relevance_score, reverse=True)[:25]
        if not s.email and s.website
    ]
    if top_no_email:
        emit_progress(
            "discovering", "enriching_contacts",
            f"Enriching contacts for {len(top_no_email)} top suppliers missing email addresses..."
        )
        from app.agents.tools.contact_enricher import enrich_supplier_contacts

        enrich_sem = asyncio.Semaphore(5)

        async def _enrich_light(supplier: DiscoveredSupplier) -> None:
            async with enrich_sem:
                try:
                    await enrich_supplier_contacts(supplier, aggressive=False)
                except Exception:  # noqa: BLE001
                    logger.debug("Lightweight enrichment failed for %s", supplier.name, exc_info=True)

        await asyncio.gather(
            *[_enrich_light(s) for s in top_no_email],
            return_exceptions=True,
        )
        enriched_count = sum(1 for s in top_no_email if s.email)
        logger.info("  Lightweight enrichment: %d/%d suppliers got emails", enriched_count, len(top_no_email))
        if enriched_count:
            emit_progress(
                "discovering", "enrichment_done",
                f"Found email addresses for {enriched_count}/{len(top_no_email)} suppliers"
            )

    # ── Finalize ──────────────────────────────────────────────
    emit_progress("discovering", "complete",
                  f"Discovery complete: {len(main_suppliers)} suppliers from {len(sources_searched)} sources"
                  + (f" ({len(filtered_suppliers)} filtered)" if filtered_suppliers else ""))

    logger.info("✅ Discovery complete: %d suppliers (+%d filtered), %d search rounds, %d intermediaries resolved",
                len(main_suppliers), len(filtered_suppliers), search_rounds, intermediaries_resolved)

    return DiscoveryResults(
        suppliers=main_suppliers,
        filtered_suppliers=filtered_suppliers,
        sources_searched=sources_searched,
        sources_failed=sources_failed,
        total_raw_results=len(all_raw),
        deduplicated_count=len(main_suppliers),
        regional_results=regional_counts,
        intermediaries_resolved=intermediaries_resolved,
        search_rounds=search_rounds,
    )
