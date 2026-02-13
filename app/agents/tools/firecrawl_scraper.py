"""Firecrawl-based web scraping tool for supplier discovery and verification."""

import httpx
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v1/search"


async def scrape_website(url: str, max_length: int = 8000) -> dict:
    """
    Scrape a website using Firecrawl, returning clean markdown.

    Args:
        url: Website URL to scrape
        max_length: Max chars of content to return

    Returns:
        Dict with markdown content, title, metadata
    """
    logger.info("  Firecrawl scraping: %s", url)
    if not settings.firecrawl_api_key:
        logger.warning("  Firecrawl API key not configured")
        return {"error": "Firecrawl API key not configured", "content": ""}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
    }
    body = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(FIRECRAWL_SCRAPE_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, Exception) as e:
            return {"error": str(e), "content": ""}

    result = data.get("data", {})
    content = result.get("markdown", "")[:max_length]

    logger.info("  Firecrawl scraped %d chars from %s", len(content), url)
    return {
        "content": content,
        "title": result.get("metadata", {}).get("title", ""),
        "description": result.get("metadata", {}).get("description", ""),
        "url": url,
        "status_code": result.get("metadata", {}).get("statusCode"),
    }


async def search_web(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """
    Search the web via Firecrawl search, returning scraped results.

    Args:
        query: Search query
        max_results: Number of results

    Returns:
        List of search results with content
    """
    logger.info("  Firecrawl web search: '%s'", query)
    if not settings.firecrawl_api_key:
        logger.warning("  Firecrawl API key not configured")
        return []

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
    }
    body = {
        "query": query,
        "limit": max_results,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(FIRECRAWL_SEARCH_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, Exception) as e:
            logger.error("  Firecrawl search failed: %s", e)
            return []

    results = []
    for item in data.get("data", []):
        results.append({
            "title": item.get("metadata", {}).get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("markdown", "")[:5000],
            "description": item.get("metadata", {}).get("description", ""),
        })

    logger.info("  Firecrawl search: %d results for '%s'", len(results), query[:50])
    return results
