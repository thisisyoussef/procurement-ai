"""Headless browser integration for visual website analysis.

Uses Browserless API to take screenshots of supplier websites,
then feeds them to Claude Vision for contact information extraction.
Falls back gracefully when API key is not configured.
"""

import base64
import json
import logging
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.llm_gateway import call_llm

settings = get_settings()
logger = logging.getLogger(__name__)

BROWSERLESS_SCREENSHOT_URL = "https://chrome.browserless.io/screenshot"

VISION_PROMPT = (Path(__file__).parent.parent / "prompts" / "contact_enrichment.md").read_text()


async def screenshot_page(url: str, full_page: bool = False) -> bytes | None:
    """Take a screenshot of a URL via Browserless API.

    Args:
        url: Page URL to screenshot.
        full_page: If True, capture the full scrollable page.

    Returns:
        PNG image bytes, or None on failure.
    """
    if not settings.browserless_api_key:
        logger.debug("Browserless API key not configured — skipping screenshot")
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
    """Screenshot a supplier's contact page(s) and extract contact info via vision.

    Tries the main URL first, then common contact page paths.

    Returns:
        Dict with aggregated contact info from visual analysis.
    """
    if not settings.browserless_api_key:
        return {"emails": [], "phones": [], "error": "browserless_not_configured"}

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
        screenshot = await screenshot_page(candidate_url)
        if not screenshot:
            continue

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

    return {
        "emails": list(set(all_emails)),
        "phones": list(set(all_phones)),
        "confidence": best_confidence,
        "source": "visual_analysis",
    }
