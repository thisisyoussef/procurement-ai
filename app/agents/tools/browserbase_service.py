"""Browserbase + Playwright cloud browser service.

Provides full headless browser sessions via Browserbase's cloud infrastructure
with Playwright for rich interaction: navigation, screenshots, form filling,
content extraction from JS-heavy sites, and more.

Replaces the simpler Browserless HTTP API with a full browser automation layer.
Falls back gracefully when API key is not configured.
"""

import asyncio
import base64
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.llm_gateway import call_llm

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

VISION_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "contact_enrichment.md"
).read_text()

# Global semaphore — set to 1 for Browserbase free tier (1 concurrent session).
# Bump to 3-5 on a paid plan.
_session_semaphore = asyncio.Semaphore(1)

# Max retries for 429 (rate limit) errors with short backoff
_MAX_SESSION_RETRIES = 3
_RETRY_BASE_DELAY_S = 3  # seconds — doubles each retry (3s, 6s, 12s)

# Page load timeout in milliseconds
PAGE_LOAD_TIMEOUT_MS = 30_000

# Known JS-heavy domains that benefit from full browser sessions
JS_HEAVY_DOMAINS = {
    "alibaba.com", "1688.com", "made-in-china.com", "dhgate.com",
    "globalsources.com", "indiamart.com", "tradeindia.com",
    "thomasnet.com", "europages.com", "ec21.com",
}


# ── Session management ───────────────────────────────────────────

def _is_configured() -> bool:
    """Check if Browserbase is configured."""
    return bool(settings.browserbase_api_key and settings.browserbase_project_id)


async def _create_session(
    *,
    proxy: bool = False,
    stealth: bool = True,
) -> object:
    """Create a new Browserbase session with short-backoff retry on 429.

    The Browserbase SDK's built-in retry waits 58+ seconds on 429 errors,
    which stalls the pipeline. Instead we catch 429s ourselves and retry
    with exponential backoff (3s → 6s → 12s) before giving up.

    Returns the session object from the Browserbase SDK with
    .id and .connect_url attributes.
    """
    from browserbase import Browserbase

    bb = Browserbase(
        api_key=settings.browserbase_api_key,
        max_retries=0,  # Disable SDK's built-in retry — we handle it ourselves
    )

    browser_settings = {
        "solveCaptchas": True,
        "recordSession": False,
    }

    create_kwargs = {
        "project_id": settings.browserbase_project_id,
        "browser_settings": browser_settings,
    }

    if proxy:
        create_kwargs["proxies"] = True

    last_error = None
    for attempt in range(_MAX_SESSION_RETRIES):
        try:
            session = bb.sessions.create(**create_kwargs)
            logger.info(
                "Browserbase session created: %s (replay: https://browserbase.com/sessions/%s)",
                session.id, session.id,
            )
            return session
        except Exception as e:
            last_error = e
            error_str = str(e)
            # Check for 429 rate limit
            if "429" in error_str or "concurrent" in error_str.lower():
                delay = _RETRY_BASE_DELAY_S * (2 ** attempt)
                logger.warning(
                    "Browserbase 429 rate limit (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, _MAX_SESSION_RETRIES, delay, error_str[:120],
                )
                await asyncio.sleep(delay)
            else:
                # Non-retryable error — raise immediately
                raise

    raise last_error  # type: ignore[misc]


async def _connect_playwright(session) -> tuple:
    """Connect async Playwright to a Browserbase session via CDP.

    Returns (playwright_instance, browser, context, page) tuple.
    """
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(session.connect_url)
    context = browser.contexts[0]
    page = context.pages[0]

    # Set default timeout
    page.set_default_timeout(PAGE_LOAD_TIMEOUT_MS)

    return pw, browser, context, page


async def _close_session(session_id: str) -> None:
    """Close a Browserbase session."""
    try:
        from browserbase import Browserbase
        bb = Browserbase(api_key=settings.browserbase_api_key)
        bb.sessions.update(session_id, status="REQUEST_RELEASE")
        logger.debug("Browserbase session released: %s", session_id)
    except Exception as e:
        logger.warning("Failed to release session %s: %s", session_id, e)


async def _with_page(
    callback,
    *,
    proxy: bool = False,
    stealth: bool = True,
    timeout_s: float = 60,
):
    """Run a callback with a Browserbase page, handling lifecycle.

    Acquires a session slot from the semaphore (queues if slot is busy),
    creates a session with 429 retry logic, connects Playwright, runs the
    callback, and cleans up.

    Args:
        callback: Async function that takes (page) and returns a result.
        proxy: Enable residential proxy.
        stealth: Enable stealth mode (default True).
        timeout_s: Max total wall-clock time for this operation (default 60s).

    Returns:
        The result of the callback, or None on failure.
    """
    if not _is_configured():
        logger.debug("Browserbase not configured — skipping")
        return None

    t0 = time.monotonic()

    # Wait for a semaphore slot — but don't wait forever
    try:
        await asyncio.wait_for(
            _session_semaphore.acquire(),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        logger.warning("Browserbase semaphore timeout after %.0fs — skipping", timeout_s)
        return None

    session = None
    pw = None
    browser = None
    try:
        remaining = timeout_s - (time.monotonic() - t0)
        if remaining <= 5:
            logger.warning("Browserbase: not enough time left after queue wait — skipping")
            return None

        session = await _create_session(proxy=proxy, stealth=stealth)
        pw, browser, context, page = await _connect_playwright(session)

        # Run the actual work with remaining time budget
        remaining = timeout_s - (time.monotonic() - t0)
        result = await asyncio.wait_for(callback(page), timeout=max(10, remaining))
        return result
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - t0
        logger.warning("Browserbase operation timed out after %.1fs", elapsed)
        return None
    except Exception as e:
        logger.error("Browserbase session error: %s", e)
        return None
    finally:
        _session_semaphore.release()
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if pw:
            try:
                await pw.stop()
            except Exception:
                pass
        if session:
            await _close_session(session.id)


# ── Public API (same signatures as browser_service.py) ───────────


async def screenshot_page(url: str, full_page: bool = False) -> bytes | None:
    """Take a screenshot of a URL via Browserbase + Playwright.

    Args:
        url: Page URL to screenshot.
        full_page: If True, capture the full scrollable page.

    Returns:
        PNG image bytes, or None on failure.
    """
    logger.info("  [Browserbase] Taking screenshot: %s", url)

    async def _take_screenshot(page):
        await page.goto(url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
        screenshot = await page.screenshot(full_page=full_page, type="png")
        logger.info("  [Browserbase] Screenshot captured: %d bytes from %s", len(screenshot), url)
        return screenshot

    return await _with_page(_take_screenshot)


async def get_rendered_html(url: str) -> str | None:
    """Fetch the fully rendered HTML after JS execution.

    Returns:
        Rendered HTML string, or None on failure.
    """
    logger.info("  [Browserbase] Fetching rendered HTML: %s", url)

    async def _get_html(page):
        await page.goto(url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
        html = await page.content()
        logger.info("  [Browserbase] Rendered HTML: %d chars from %s", len(html), url)
        return html

    return await _with_page(_get_html)


def _extract_emails_from_html(html: str) -> list[str]:
    """Regex-extract email addresses from raw HTML content."""
    if not html:
        return []
    found = EMAIL_REGEX.findall(html)
    return list({e.lower() for e in found})


async def browse_for_contacts(url: str) -> dict:
    """Navigate a supplier's website to find contact information.

    Enhanced over the old Browserless approach: instead of guessing URL suffixes,
    this uses Playwright to find actual contact links in the navigation, dismiss
    cookie banners, and scroll to load lazy content.

    Returns:
        Dict with aggregated contact info from visual + HTML analysis.
    """
    if not _is_configured():
        return {"emails": [], "phones": [], "error": "browserbase_not_configured"}

    logger.info("  [Browserbase] Browsing for contacts: %s", url)

    async def _browse(page):
        all_emails: list[str] = []
        all_phones: list[str] = []
        best_confidence = 0

        # Navigate to homepage first
        await page.goto(url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)

        # Try to dismiss cookie consent banners
        await _dismiss_cookie_banner(page)

        # Strategy 1: Try to find and click actual contact links in nav
        contact_url = await _find_contact_link(page, url)

        # Strategy 2: Fall back to known contact URL patterns
        if not contact_url:
            base = url.rstrip("/")
            contact_candidates = [
                base + "/contact",
                base + "/contact-us",
                base + "/about",
                base + "/about-us",
            ]
        else:
            contact_candidates = [contact_url]

        # Visit contact pages and extract
        pages_checked = 0
        for candidate_url in contact_candidates:
            if pages_checked > 0:
                # Navigate to next candidate (reuse same session)
                try:
                    await page.goto(
                        candidate_url,
                        wait_until="networkidle",
                        timeout=PAGE_LOAD_TIMEOUT_MS,
                    )
                except Exception:
                    continue

            pages_checked += 1

            # Scroll down to trigger lazy-loaded content
            await _scroll_page(page)

            # Extract emails from rendered HTML
            html = await page.content()
            html_emails = _extract_emails_from_html(html)
            all_emails.extend(html_emails)
            if html_emails:
                logger.info(
                    "  [Browserbase] HTML regex: %d emails from %s",
                    len(html_emails), candidate_url,
                )

            # Take screenshot for Claude Vision extraction
            try:
                screenshot = await page.screenshot(full_page=False, type="png")
                result = await _extract_contacts_from_screenshot(
                    screenshot, candidate_url
                )
                emails = result.get("emails", [])
                phones = result.get("phones", [])
                confidence = result.get("confidence", 0)

                all_emails.extend(emails)
                all_phones.extend(phones)
                best_confidence = max(best_confidence, confidence)

                # Short-circuit if we found good contact info
                if emails and confidence >= 70:
                    break
            except Exception as e:
                logger.warning(
                    "  [Browserbase] Vision extraction failed for %s: %s",
                    candidate_url, e,
                )

            # If HTML regex already found emails, we can stop
            if all_emails and pages_checked >= 2:
                break

        return {
            "emails": list(set(all_emails)),
            "phones": list(set(all_phones)),
            "confidence": best_confidence,
            "source": "browserbase_visual_analysis",
        }

    return await _with_page(_browse) or {
        "emails": [],
        "phones": [],
        "error": "session_failed",
    }


# ── Helper functions ─────────────────────────────────────────────


async def _dismiss_cookie_banner(page) -> None:
    """Try to dismiss cookie consent banners that may block content."""
    cookie_selectors = [
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("Accept Cookies")',
        'button:has-text("I Accept")',
        'button:has-text("Got it")',
        'button:has-text("OK")',
        'button:has-text("Agree")',
        '[id*="cookie"] button',
        '[class*="cookie"] button',
        '[id*="consent"] button',
        '[class*="consent"] button',
    ]
    for selector in cookie_selectors:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1000):
                await btn.click(timeout=2000)
                logger.debug("  [Browserbase] Dismissed cookie banner via: %s", selector)
                await page.wait_for_timeout(500)
                return
        except Exception:
            continue


async def _find_contact_link(page, base_url: str) -> str | None:
    """Search the current page for a contact/about link in navigation."""
    contact_patterns = [
        "Contact", "Contact Us", "Get in Touch", "Reach Us",
        "About", "About Us", "Get a Quote", "Request Quote",
        "Inquiry", "Enquiry",
    ]
    for pattern in contact_patterns:
        try:
            link = page.get_by_role("link", name=re.compile(pattern, re.IGNORECASE)).first
            href = await link.get_attribute("href", timeout=1000)
            if href:
                # Resolve relative URLs
                if href.startswith("/"):
                    parsed = urlparse(base_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                elif not href.startswith("http"):
                    href = base_url.rstrip("/") + "/" + href
                logger.debug("  [Browserbase] Found contact link: %s", href)
                return href
        except Exception:
            continue
    return None


async def _scroll_page(page, scroll_count: int = 3) -> None:
    """Scroll down the page to trigger lazy-loaded content."""
    for _ in range(scroll_count):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(300)


async def _extract_contacts_from_screenshot(
    screenshot_bytes: bytes,
    url: str,
) -> dict:
    """Send a website screenshot to Claude Vision for contact info extraction."""
    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    logger.info("  [Browserbase] Sending screenshot to Vision for contact extraction (%s)", url)
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
        logger.warning("  [Browserbase] Could not parse vision response as JSON")
        data = {"emails": [], "phones": [], "confidence": 0}

    logger.info(
        "  [Browserbase] Vision extraction: %d emails, %d phones (confidence: %s)",
        len(data.get("emails", [])),
        len(data.get("phones", [])),
        data.get("confidence", "?"),
    )
    return data


# ── Cost gating ──────────────────────────────────────────────────


def should_use_browserbase(url: str) -> bool:
    """Decide if a URL warrants a full Browserbase session.

    Use Browserbase for JS-heavy sites, known complex domains.
    Use Firecrawl for simple static pages.
    """
    if not _is_configured():
        return False

    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = (parsed.hostname or "").lstrip("www.")
        parts = host.split(".")
        domain = ".".join(parts[-2:]) if len(parts) >= 2 else host
        return domain in JS_HEAVY_DOMAINS
    except Exception:
        return False
