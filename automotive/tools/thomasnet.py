"""Thomasnet search via Browserbase headless browser automation."""

import logging
import uuid

from app.core.config import get_settings
from automotive.schemas.discovery import DiscoveredSupplier

logger = logging.getLogger(__name__)


async def search_thomasnet(query: str) -> list[DiscoveredSupplier]:
    """Search Thomasnet for industrial suppliers via Browserbase.

    Thomasnet has no public API, so we use Browserbase cloud browser
    instances to automate the search. Falls back to web search if
    Browserbase is not configured.
    """
    settings = get_settings()
    if not settings.browserbase_api_key or not settings.browserbase_project_id:
        logger.info("Browserbase not configured, skipping Thomasnet search")
        return []

    suppliers = []
    try:
        from browserbase import Browserbase

        bb = Browserbase(api_key=settings.browserbase_api_key)
        session = bb.sessions.create(project_id=settings.browserbase_project_id)

        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0]

            # Navigate to Thomasnet search
            search_url = f"https://www.thomasnet.com/nsearch.html?cov=NA&what={query.replace(' ', '+')}"
            await page.goto(search_url, timeout=30000)
            await page.wait_for_load_state("domcontentloaded")

            # Extract supplier cards
            cards = await page.query_selector_all(".supplier-search-result, .company-card, [data-testid='supplier-card']")

            for card in cards[:20]:
                name_el = await card.query_selector("h2, .company-name, [data-testid='company-name']")
                name = await name_el.inner_text() if name_el else ""
                if not name:
                    continue

                loc_el = await card.query_selector(".supplier-location, .company-location")
                location = await loc_el.inner_text() if loc_el else ""

                link_el = await card.query_selector("a[href*='thomasnet.com/profile']")
                website = await link_el.get_attribute("href") if link_el else None

                suppliers.append(DiscoveredSupplier(
                    supplier_id=str(uuid.uuid4()),
                    company_name=name.strip(),
                    headquarters=location.strip(),
                    website=website,
                    sources=["thomasnet"],
                    data_richness=50,
                ))

            await browser.close()

        bb.sessions.update(session.id, project_id=settings.browserbase_project_id, status="REQUEST_RELEASE")
        logger.info("Thomasnet returned %d results for: %s", len(suppliers), query)

    except ImportError:
        logger.warning("Browserbase/Playwright not available, skipping Thomasnet")
    except Exception:
        logger.exception("Thomasnet search failed for: %s", query)

    return suppliers
