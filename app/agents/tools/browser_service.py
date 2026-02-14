"""Headless browser integration for visual website analysis.

Uses Browserless API to take screenshots of supplier websites,
then feeds them to Claude Vision for contact information extraction.
Also extracts the rendered page HTML for regex-based email extraction
(catches JS-rendered content that static scrapers miss).
Falls back gracefully when API key is not configured.
"""

import asyncio
import base64
import json
import logging
import re
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.llm_gateway import call_llm

settings = get_settings()
logger = logging.getLogger(__name__)

BROWSERLESS_SCREENSHOT_URL = "https://chrome.browserless.io/screenshot"
BROWSERLESS_CONTENT_URL = "https://chrome.browserless.io/content"

VISION_PROMPT = (Path(__file__).parent.parent / "prompts" / "contact_enrichment.md").read_text()

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)


async def screenshot_page(url: str, full_page: bool = False) -> bytes | None:
    """Take a screenshot of a URL via Browserbase (preferred) or Browserless (fallback).

    Args:
        url: Page URL to screenshot.
        full_page: If True, capture the full scrollable page.

    Returns:
        PNG image bytes, or None on failure.
    """
    # Prefer Browserbase when configured
    if settings.browserbase_api_key:
        from .browserbase_service import screenshot_page as bb_screenshot
        return await bb_screenshot(url, full_page)

    if not settings.browserless_api_key:
        logger.debug("No browser service configured — skipping screenshot")
        return None

    logger.info("  Taking screenshot: %s", url)
    params = {"token": settings.browserless_api_key}
    body = {
        "url": url,
        "options": {
            "fullPage": full_page,
            "type": "png",
        },
        "gotoOptions": {
            "waitUntil": "networkidle2",
            "timeout": 15000,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                BROWSERLESS_SCREENSHOT_URL,
                params=params,
                json=body,
            )
            resp.raise_for_status()
            logger.info("  Screenshot captured: %d bytes from %s", len(resp.content), url)
            return resp.content
        except (httpx.HTTPError, Exception) as e:
            logger.warning("  Screenshot failed for %s: %s", url, e)
            return None


async def get_rendered_html(url: str) -> str | None:
    """Fetch the fully rendered HTML of a page via Browserbase (preferred) or Browserless (fallback).

    This returns the DOM after JavaScript execution — useful for extracting
    emails from JS-rendered websites that static scrapers (httpx) cannot see.

    Returns:
        Rendered HTML string, or None on failure.
    """
    # Prefer Browserbase when configured
    if settings.browserbase_api_key:
        from .browserbase_service import get_rendered_html as bb_get_html
        return await bb_get_html(url)

    if not settings.browserless_api_key:
        return None

    logger.info("  Fetching rendered HTML: %s", url)
    params = {"token": settings.browserless_api_key}
    body = {
        "url": url,
        "gotoOptions": {
            "waitUntil": "networkidle2",
            "timeout": 15000,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                BROWSERLESS_CONTENT_URL,
                params=params,
                json=body,
            )
            resp.raise_for_status()
            html = resp.text
            logger.info("  Rendered HTML: %d chars from %s", len(html), url)
            return html
        except (httpx.HTTPError, Exception) as e:
            logger.warning("  Rendered HTML fetch failed for %s: %s", url, e)
            return None


def _extract_emails_from_html(html: str) -> list[str]:
    """Regex-extract email addresses from raw HTML content."""
    if not html:
        return []
    found = EMAIL_REGEX.findall(html)
    # Deduplicate and lowercase
    return list({e.lower() for e in found})


async def extract_contacts_from_screenshot(
    screenshot_bytes: bytes,
    url: str,
) -> dict:
    """Send a website screenshot to Claude Vision for contact info extraction.

    Args:
        screenshot_bytes: PNG image bytes.
        url: The URL that was screenshotted (for context).

    Returns:
        Dict with extracted contact info (emails, phones, etc.).
    """
    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    logger.info("  Sending screenshot to Claude Vision for contact extraction (%s)", url)
    response = await call_llm(
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"Extract all contact information from this website screenshot.\n"
                        f"URL: {url}\n\n"
                        f"Return ONLY a JSON object with the extracted data."
                    ),
                },
            ],
        }],
        system=VISION_PROMPT,
        model=settings.model_cheap,
        max_tokens=500,
    )

    # Parse the vision response
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    try:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("  Could not parse vision response as JSON")
        data = {"emails": [], "phones": [], "confidence": 0}

    logger.info(
        "  Vision extraction: %d emails, %d phones (confidence: %s)",
        len(data.get("emails", [])),
        len(data.get("phones", [])),
        data.get("confidence", "?"),
    )
    return data


async def browse_for_contacts(url: str) -> dict:
    """Navigate a supplier's website and extract contact info via
    vision AND rendered HTML regex scanning.

    Uses Browserbase (preferred) or Browserless (fallback).
    Browserbase provides enhanced navigation: finds real contact links,
    dismisses cookie banners, scrolls for lazy content.

    Returns:
        Dict with aggregated contact info from visual + HTML analysis.
    """
    # Prefer Browserbase when configured
    if settings.browserbase_api_key:
        from .browserbase_service import browse_for_contacts as bb_browse
        return await bb_browse(url)

    if not settings.browserless_api_key:
        return {"emails": [], "phones": [], "error": "browser_not_configured"}

    # Build candidate contact URLs
    base = url.rstrip("/")
    candidates = [
        base + "/contact",
        base + "/contact-us",
        base + "/about",
        base + "/about-us",
        base,  # Try homepage last
    ]

    all_emails: list[str] = []
    all_phones: list[str] = []
    best_confidence = 0

    for candidate_url in candidates:
        # Run screenshot and HTML fetch in parallel for the same URL
        screenshot_task = screenshot_page(candidate_url)
        html_task = get_rendered_html(candidate_url)
        screenshot, rendered_html = await asyncio.gather(screenshot_task, html_task)

        # Extract from rendered HTML via regex (catches JS-rendered emails)
        if rendered_html:
            html_emails = _extract_emails_from_html(rendered_html)
            all_emails.extend(html_emails)
            if html_emails:
                logger.info("  Rendered HTML regex: %d emails from %s", len(html_emails), candidate_url)

        # Extract from screenshot via Claude Vision
        if screenshot:
            result = await extract_contacts_from_screenshot(screenshot, candidate_url)
            emails = result.get("emails", [])
            phones = result.get("phones", [])
            confidence = result.get("confidence", 0)

            all_emails.extend(emails)
            all_phones.extend(phones)
            best_confidence = max(best_confidence, confidence)

            # Short-circuit if we found good contact info
            if emails and confidence >= 70:
                break

        # If HTML regex already found emails, still try vision for confidence
        # but don't need to check more pages
        if all_emails and not screenshot:
            break

    return {
        "emails": list(set(all_emails)),
        "phones": list(set(all_phones)),
        "confidence": best_confidence,
        "source": "visual_analysis",
    }
