"""Firecrawl-powered web search and extraction for supplier discovery."""

import logging
import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from automotive.schemas.discovery import DiscoveredSupplier

logger = logging.getLogger(__name__)


async def search_web_firecrawl(query: str) -> list[DiscoveredSupplier]:
    """Use Firecrawl to search the web for automotive suppliers."""
    settings = get_settings()
    if not settings.firecrawl_api_key:
        logger.warning("Firecrawl API key not configured, skipping web search")
        return []

    suppliers = []
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/search",
                headers={
                    "Authorization": f"Bearer {settings.firecrawl_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "limit": 10,
                    "scrapeOptions": {"formats": ["markdown"]},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        for item in data.get("data", []):
            title = item.get("metadata", {}).get("title", "")
            url = item.get("metadata", {}).get("sourceURL", "")

            if not title:
                continue

            # Extract company name from title (heuristic: before dash or pipe)
            company_name = title.split("|")[0].split("–")[0].split("-")[0].strip()
            if len(company_name) > 100:
                company_name = company_name[:100]

            suppliers.append(DiscoveredSupplier(
                supplier_id=str(uuid.uuid4()),
                company_name=company_name,
                website=url,
                sources=["web_search"],
                data_richness=30,
            ))

        logger.info("Firecrawl web search returned %d results for: %s", len(suppliers), query)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 402, 403):
            logger.warning("Firecrawl billing/auth error (%s) — skipping web search for: %s", e.response.status_code, query)
        else:
            logger.exception("Firecrawl web search failed for: %s", query)
    except Exception:
        logger.exception("Firecrawl web search failed for: %s", query)

    return suppliers


async def extract_supplier_capabilities(website_url: str) -> dict[str, Any]:
    """Extract structured capabilities from a supplier's website using Firecrawl."""
    settings = get_settings()
    if not settings.firecrawl_api_key:
        return {}

    schema = {
        "type": "object",
        "properties": {
            "company_description": {"type": "string"},
            "manufacturing_processes": {"type": "array", "items": {"type": "string"}},
            "materials_processed": {"type": "array", "items": {"type": "string"}},
            "equipment_list": {"type": "array", "items": {"type": "string"}},
            "certifications_claimed": {"type": "array", "items": {"type": "string"}},
            "industries_served": {"type": "array", "items": {"type": "string"}},
            "key_customers": {"type": "array", "items": {"type": "string"}},
            "capacity_indicators": {"type": "array", "items": {"type": "string"}},
            "secondary_operations": {"type": "array", "items": {"type": "string"}},
            "prototype_capability": {"type": "boolean"},
            "geographic_notes": {"type": "string"},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {settings.firecrawl_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": website_url,
                    "formats": ["extract"],
                    "extract": {"schema": schema},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        extract = data.get("data", {}).get("extract", {})
        logger.info("Extracted capabilities from %s: %d fields", website_url, len(extract))
        return extract
    except Exception:
        logger.exception("Firecrawl extraction failed for: %s", website_url)
        return {}
