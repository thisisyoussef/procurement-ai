"""Intermediary / directory site detection and direct manufacturer resolution.

When discovery finds suppliers listed on directory sites (Alibaba, ThomasNet, etc.),
this module detects them and attempts to resolve the actual manufacturer's direct website.

Two-tier detection:
1. URL pattern matching against known intermediary domains (instant, free)
2. LLM classification for ambiguous cases (Haiku, cheap)
"""

import json
import logging
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.agents.tools.firecrawl_scraper import search_web
from app.schemas.agent_state import IntermediaryDetection

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Known intermediary / directory / marketplace domains ──────────

KNOWN_INTERMEDIARY_DOMAINS: set[str] = {
    # Chinese marketplaces
    "alibaba.com", "1688.com", "made-in-china.com", "dhgate.com",
    "globalsources.com", "hktdc.com",
    # Indian marketplaces
    "indiamart.com", "tradeindia.com", "exportersindia.com",
    "justdial.com",
    # Western directories
    "thomasnet.com", "forsource.com", "kompass.com", "europages.com",
    "mfg.com", "dnb.com", "yellowpages.com",
    # Southeast Asian
    "tradewheel.com", "ec21.com", "ecplaza.net",
    # General B2B
    "go4worldbusiness.com", "tradekey.com", "wholesalecentral.com",
    "sourcify.com", "maker-s-row.com", "makersrow.com",
    # Aggregators / review sites
    "yelp.com", "bbb.org", "trustpilot.com",
}


def _extract_domain(url: str) -> str:
    """Extract the root domain from a URL."""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = parsed.hostname or ""
        # Strip www. and get root domain (last two parts)
        parts = host.lstrip("www.").split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host
    except Exception:
        return ""


def detect_intermediary_by_url(url: str | None) -> tuple[bool, str | None]:
    """Fast check: is this URL from a known intermediary domain?

    Returns:
        (is_intermediary, intermediary_type)
    """
    if not url:
        return False, None

    domain = _extract_domain(url)
    if domain in KNOWN_INTERMEDIARY_DOMAINS:
        # Classify type based on domain
        marketplaces = {"alibaba.com", "1688.com", "dhgate.com", "indiamart.com",
                        "made-in-china.com", "globalsources.com", "tradewheel.com",
                        "ec21.com", "tradeindia.com"}
        if domain in marketplaces:
            return True, "marketplace"
        return True, "directory"

    return False, None


async def classify_intermediary_by_content(
    name: str,
    description: str | None,
    url: str | None,
    page_content: str | None = None,
) -> IntermediaryDetection:
    """LLM-based classification for ambiguous cases.

    Uses Haiku for cheap classification.
    """
    content_snippet = (page_content or "")[:1500]
    prompt = f"""Classify this supplier entry:

Name: {name}
URL: {url or "N/A"}
Description: {(description or "N/A")[:500]}
Page content snippet: {content_snippet[:800] if content_snippet else "N/A"}

Is this:
A) A DIRECT MANUFACTURER / FACTORY that makes products themselves
B) A DIRECTORY / MARKETPLACE that lists multiple manufacturers (like Alibaba, ThomasNet)
C) A TRADING COMPANY / MIDDLEMAN that resells from factories

Respond with JSON:
{{"is_intermediary": true/false, "intermediary_type": "directory"|"marketplace"|"trading_company"|null, "extracted_manufacturer_name": "actual factory name if visible"|null}}"""

    try:
        response = await call_llm_structured(
            prompt=prompt,
            system="You classify supplier entries. Respond ONLY with valid JSON.",
            model=settings.model_cheap,
            max_tokens=300,
        )
        data = json.loads(response.strip().strip("`").strip())
        return IntermediaryDetection(
            is_intermediary=data.get("is_intermediary", False),
            intermediary_type=data.get("intermediary_type"),
            original_url=url,
            extracted_manufacturer_name=data.get("extracted_manufacturer_name"),
        )
    except Exception as e:
        logger.warning("Intermediary classification failed for %s: %s", name, e)
        return IntermediaryDetection(is_intermediary=False, original_url=url)


async def extract_manufacturers_from_listing(
    page_content: str,
    product_type: str,
) -> list[str]:
    """Extract actual manufacturer / factory names from a directory listing page."""
    prompt = f"""This is content from a supplier directory page. Extract the names of actual manufacturers/factories
that produce "{product_type}". Only include company names that appear to be real manufacturers, not the directory itself.

Content:
{page_content[:3000]}

Return a JSON array of manufacturer names (max 5). Example: ["ABC Manufacturing Co.", "XYZ Factory Ltd."]
Return ONLY the JSON array."""

    try:
        response = await call_llm_structured(
            prompt=prompt,
            system="Extract manufacturer names from directory content. Return a JSON array.",
            model=settings.model_cheap,
            max_tokens=500,
        )
        text = response.strip().strip("`")
        names = json.loads(text)
        if isinstance(names, list):
            return [n for n in names if isinstance(n, str) and len(n) > 2][:5]
    except Exception as e:
        logger.warning("Failed to extract manufacturers from listing: %s", e)

    return []


async def resolve_direct_website(
    manufacturer_name: str,
    product_type: str,
) -> str | None:
    """Search for a manufacturer's official website via Firecrawl web search.

    Returns the best direct URL, or None if not found.
    """
    query = f'"{manufacturer_name}" official website {product_type}'
    logger.info("  Resolving direct website for: %s", manufacturer_name)

    try:
        results = await search_web(query, max_results=3)
        if not results:
            return None

        # Filter out known intermediary domains
        for r in results:
            url = r.get("url", "")
            domain = _extract_domain(url)
            if domain and domain not in KNOWN_INTERMEDIARY_DOMAINS:
                logger.info("  Resolved %s → %s", manufacturer_name, url)
                return url

    except Exception as e:
        logger.warning("  Direct website resolution failed for %s: %s", manufacturer_name, e)

    return None
