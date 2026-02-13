"""Fallback web search using httpx + scraping for when Firecrawl isn't available."""

import httpx
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("app.agents.tools.web_search")


async def scrape_url_basic(url: str, max_length: int = 5000) -> dict:
    """
    Basic website scraping fallback without Firecrawl.
    Uses httpx + BeautifulSoup.
    """
    logger.info("  Basic scraping: %s", url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; Tamkin/1.0; +https://tamkin.ai)"
        )
    }
    async with httpx.AsyncClient(
        timeout=15.0, follow_redirects=True, headers=headers
    ) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as e:
            logger.error("  Basic scrape failed for %s: %s", url, e)
            return {"error": str(e), "content": "", "url": url}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = soup.title.string if soup.title else ""
    text = soup.get_text(separator="\n", strip=True)[:max_length]

    # Extract meta description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    # Extract contact info patterns
    emails = []
    phones = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("mailto:"):
            emails.append(href.replace("mailto:", "").split("?")[0])
        elif href.startswith("tel:"):
            phones.append(href.replace("tel:", ""))

    logger.info("  Scraped %d chars, %d emails, %d phones from %s", len(text), len(emails), len(phones), url)
    return {
        "content": text,
        "title": title,
        "description": meta_desc,
        "url": url,
        "emails": list(set(emails)),
        "phones": list(set(phones)),
        "has_ssl": url.startswith("https"),
    }
