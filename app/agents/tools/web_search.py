"""Fallback web search using httpx + scraping for when Firecrawl isn't available."""

import re
import httpx
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("app.agents.tools.web_search")

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
PHONE_REGEX = re.compile(
    r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}"
)


async def scrape_url_basic(url: str, max_length: int = 8000) -> dict:
    """
    Basic website scraping fallback without Firecrawl.
    Uses httpx + BeautifulSoup.

    Extracts emails and phone numbers from the FULL HTML (including
    footer, header, nav) before cleaning the content for text extraction.
    """
    logger.info("  Basic scraping: %s", url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ProcurementAI/1.0; +https://example.com/procurement-ai)"
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

    raw_html = resp.text
    soup = BeautifulSoup(raw_html, "html.parser")

    # ── Extract contact info from FULL HTML before any tag removal ──
    # This ensures footer/header/nav emails and phones are captured.
    emails = []
    phones = []

    # 1) mailto: and tel: links from the full document
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("mailto:"):
            emails.append(href.replace("mailto:", "").split("?")[0])
        elif href.startswith("tel:"):
            phones.append(href.replace("tel:", ""))

    # 2) Regex scan the raw HTML for email addresses (catches plain-text
    #    emails in footers, paragraphs, JS data attributes, etc.)
    raw_emails = EMAIL_REGEX.findall(raw_html)
    emails.extend(raw_emails)

    # 3) Regex scan for phone numbers in the full text (before cleanup)
    full_text = soup.get_text(separator=" ", strip=True)
    raw_phones = PHONE_REGEX.findall(full_text)
    phones.extend(raw_phones)

    # ── Now clean the soup for content extraction ──────────────────
    # Remove script/style only — keep nav/footer/header for richer content
    for tag in soup(["script", "style"]):
        tag.decompose()

    title = soup.title.string if soup.title else ""
    text = soup.get_text(separator="\n", strip=True)[:max_length]

    # Extract meta description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    # Deduplicate
    unique_emails = list({e.strip().lower() for e in emails if e.strip()})
    unique_phones = list({p.strip() for p in phones if p.strip()})

    logger.info("  Scraped %d chars, %d emails, %d phones from %s", len(text), len(unique_emails), len(unique_phones), url)
    return {
        "content": text,
        "title": title,
        "description": meta_desc,
        "url": url,
        "emails": unique_emails,
        "phones": unique_phones,
        "has_ssl": url.startswith("https"),
    }
