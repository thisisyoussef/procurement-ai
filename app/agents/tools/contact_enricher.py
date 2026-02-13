"""Multi-tier waterfall contact enrichment engine.

Relentlessly finds supplier email addresses and phone numbers by chaining
progressively more expensive methods. Cheap tiers (1 & 2) always run to
accumulate the best possible email; expensive tiers (3–5) short-circuit
once a valid email is found.

Tiers:
  1. Contact page scraping (free — uses existing scrapers)
  2. Firecrawl AI extraction (existing API key)
  3. Visual analysis via headless browser + Claude Vision (Browserless)
  4. Hunter.io domain search (paid API)
  5. Google search for contact info (free — uses Firecrawl search)
"""

import asyncio
import re
import logging
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.schemas.agent_state import ContactEnrichmentResult, DiscoveredSupplier

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Email validation ─────────────────────────────────────────────

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Emails to ignore — not useful for procurement outreach
IGNORED_EMAIL_PREFIXES = {
    "noreply", "no-reply", "no_reply", "donotreply",
    "mailer-daemon", "postmaster", "webmaster",
    "abuse", "security", "privacy",
}

# Preferred email prefixes for procurement (highest priority first)
PREFERRED_PREFIXES = [
    "sales", "quote", "quotes", "rfq", "order", "orders",
    "inquiry", "enquiry", "procurement", "sourcing",
    "commercial", "export", "trade",
    "info", "contact", "hello", "general",
]


def _is_valid_email(email: str) -> bool:
    """Basic email format validation and blocklist check."""
    if not EMAIL_REGEX.fullmatch(email):
        return False
    local = email.split("@")[0].lower()
    return local not in IGNORED_EMAIL_PREFIXES


def _rank_email(email: str) -> int:
    """Lower rank = more preferred for procurement outreach."""
    local = email.split("@")[0].lower()
    for i, prefix in enumerate(PREFERRED_PREFIXES):
        if local.startswith(prefix):
            return i
    return len(PREFERRED_PREFIXES)  # Unknown prefix gets lowest priority


def _pick_best_email(emails: list[str]) -> str | None:
    """Pick the best email for procurement outreach."""
    valid = [e for e in emails if _is_valid_email(e)]
    if not valid:
        return None
    valid.sort(key=_rank_email)
    return valid[0]


def _extract_domain(url: str) -> str | None:
    """Extract the root domain from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return None


# ── Tier 1: Contact page scraping (free) ──────────────────────────

async def _tier1_scrape_contact_pages(supplier: DiscoveredSupplier) -> dict:
    """Scrape common contact pages for email/phone using existing scrapers.

    Scrapes the homepage (footer!) plus many common contact page paths
    in parallel to maximise coverage.
    """
    from app.agents.tools.web_search import scrape_url_basic

    if not supplier.website:
        return {"emails": [], "phones": [], "source": "contact_page_scrape"}

    base = supplier.website.rstrip("/")
    contact_paths = [
        "",  # homepage — footers almost always have contact info
        "/contact", "/contact-us", "/contact_us",
        "/about", "/about-us", "/about_us",
        "/reach-us", "/get-in-touch", "/enquiry",
        "/get-a-quote", "/request-quote", "/inquiry",
        "/support", "/customer-service",
    ]

    all_emails: list[str] = []
    all_phones: list[str] = []

    # Scrape contact pages in parallel (max 5 concurrent)
    sem = asyncio.Semaphore(5)

    async def _scrape(path: str):
        async with sem:
            url = base + path
            try:
                result = await scrape_url_basic(url, max_length=6000)
                # scrape_url_basic now extracts emails/phones from full HTML
                # (including footer/nav) before cleanup
                all_emails.extend(result.get("emails", []))
                all_phones.extend(result.get("phones", []))

                # Also regex-scan the page content for emails
                content = result.get("content", "")
                found = EMAIL_REGEX.findall(content)
                all_emails.extend(found)
            except Exception as e:
                logger.debug("  Tier 1: Failed to scrape %s: %s", url, e)

    tasks = [_scrape(path) for path in contact_paths]
    await asyncio.gather(*tasks, return_exceptions=True)

    emails = list({e.lower() for e in all_emails if _is_valid_email(e)})
    phones = list(set(all_phones))

    logger.info(
        "  Tier 1 (contact page scrape): %d emails, %d phones from %s",
        len(emails), len(phones), base,
    )
    return {"emails": emails, "phones": phones, "source": "contact_page_scrape"}


# ── Tier 2: Firecrawl AI extraction ───────────────────────────────

async def _tier2_firecrawl_extract(supplier: DiscoveredSupplier) -> dict:
    """Use Firecrawl's /extract endpoint with AI to pull contact info.

    Tries the /contact page first (where contact info is most likely),
    then falls back to the homepage. Includes full page content
    (footer/nav) in the extraction scope.
    """
    if not settings.firecrawl_api_key or not supplier.website:
        return {"emails": [], "phones": [], "source": "firecrawl_extract"}

    base = supplier.website.rstrip("/")
    # Try contact page first, then homepage
    urls_to_try = [base + "/contact", base]

    logger.info("  Tier 2: Firecrawl AI extraction for %s", supplier.website)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
    }

    all_emails: list[str] = []
    all_phones: list[str] = []

    for target_url in urls_to_try:
        body = {
            "url": target_url,
            "formats": ["extract"],
            "onlyMainContent": False,  # Include footer/nav/header content
            "extract": {
                "prompt": (
                    "Extract ALL contact information from this website page. "
                    "Look everywhere including the footer, header, sidebar, and pop-ups. "
                    "Find: email addresses (especially sales/quotes/orders/rfq/inquiry emails), "
                    "phone numbers, fax numbers, WhatsApp numbers, "
                    "physical address, contact form URLs, LinkedIn company page, "
                    "and names/titles of sales or procurement contacts."
                ),
                "schema": {
                    "type": "object",
                    "properties": {
                        "emails": {"type": "array", "items": {"type": "string"}},
                        "phones": {"type": "array", "items": {"type": "string"}},
                        "whatsapp": {"type": "array", "items": {"type": "string"}},
                        "address": {"type": "string"},
                        "contact_form_url": {"type": "string"},
                        "linkedin_url": {"type": "string"},
                        "contacts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "title": {"type": "string"},
                                    "email": {"type": "string"},
                                    "phone": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    json=body,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, Exception) as e:
                logger.warning("  Tier 2: Firecrawl extract failed for %s: %s", target_url, e)
                continue

        extracted = data.get("data", {}).get("extract", {})
        emails = extracted.get("emails", [])
        phones = extracted.get("phones", [])

        # Also check contacts array for additional emails
        for contact in extracted.get("contacts", []):
            if contact.get("email"):
                emails.append(contact["email"])
            if contact.get("phone"):
                phones.append(contact["phone"])

        # WhatsApp numbers are also useful phone contacts
        whatsapp = extracted.get("whatsapp", [])
        phones.extend(whatsapp)

        all_emails.extend(emails)
        all_phones.extend(phones)

        # If we found emails on the contact page, no need to try homepage
        if emails:
            logger.info("  Tier 2: Found %d emails on %s — skipping homepage", len(emails), target_url)
            break

    all_emails = list({e.lower() for e in all_emails if _is_valid_email(e)})
    all_phones = list(set(all_phones))

    logger.info(
        "  Tier 2 (Firecrawl extract): %d emails, %d phones",
        len(all_emails), len(all_phones),
    )
    return {"emails": all_emails, "phones": all_phones, "source": "firecrawl_extract"}


# ── Tier 3: Visual analysis (Browserless + Claude Vision) ─────────

async def _tier3_visual_analysis(supplier: DiscoveredSupplier) -> dict:
    """Screenshot supplier website and extract contacts via Claude Vision."""
    from app.agents.tools.browser_service import browse_for_contacts

    if not supplier.website:
        return {"emails": [], "phones": [], "source": "visual_analysis"}

    logger.info("  Tier 3: Visual analysis for %s", supplier.website)
    result = await browse_for_contacts(supplier.website)

    emails = [e.lower() for e in result.get("emails", []) if _is_valid_email(e)]
    phones = result.get("phones", [])

    logger.info(
        "  Tier 3 (visual): %d emails, %d phones (confidence: %s)",
        len(emails), len(phones), result.get("confidence", "?"),
    )
    return {"emails": emails, "phones": phones, "source": "visual_analysis"}


# ── Tier 4: Hunter.io domain search ──────────────────────────────

async def _tier4_hunter_io(supplier: DiscoveredSupplier) -> dict:
    """Search Hunter.io for all known emails at supplier's domain."""
    if not settings.hunter_api_key or not supplier.website:
        return {"emails": [], "phones": [], "source": "hunter_io"}

    domain = _extract_domain(supplier.website)
    if not domain:
        return {"emails": [], "phones": [], "source": "hunter_io"}

    logger.info("  Tier 4: Hunter.io domain search for %s", domain)

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                "https://api.hunter.io/v2/domain-search",
                params={
                    "domain": domain,
                    "api_key": settings.hunter_api_key,
                    "limit": 10,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, Exception) as e:
            logger.warning("  Tier 4: Hunter.io failed: %s", e)
            return {"emails": [], "phones": [], "source": "hunter_io"}

    emails = []
    for entry in data.get("data", {}).get("emails", []):
        email = entry.get("value", "")
        confidence = entry.get("confidence", 0)
        if email and confidence >= 50 and _is_valid_email(email):
            emails.append(email.lower())

    # Hunter also provides a generic pattern-based email
    pattern = data.get("data", {}).get("pattern")
    if pattern and not emails:
        # e.g. "{first}.{last}@domain.com" — we can't use it without a name
        logger.info("  Tier 4: Hunter found email pattern: %s (no specific emails)", pattern)

    logger.info("  Tier 4 (Hunter.io): %d emails", len(emails))
    return {"emails": emails, "phones": [], "source": "hunter_io"}


# ── Tier 5: Google search for contact info ────────────────────────

async def _tier5_google_search(supplier: DiscoveredSupplier) -> dict:
    """Search Google for the supplier's contact information.

    Runs all available queries and collects results from each
    rather than stopping at the first hit.
    """
    from app.agents.tools.firecrawl_scraper import search_web

    if not settings.firecrawl_api_key:
        return {"emails": [], "phones": [], "source": "google_search"}

    # Build targeted search queries
    queries = [
        f'"{supplier.name}" email contact',
        f'"{supplier.name}" sales email phone',
    ]
    if supplier.website:
        domain = _extract_domain(supplier.website)
        if domain:
            queries.append(f"site:{domain} contact email")
            queries.append(f'"{supplier.name}" "{domain}" contact email phone')

    logger.info("  Tier 5: Google search for contacts of %s (%d queries)", supplier.name, len(queries))

    all_emails: list[str] = []
    all_phones: list[str] = []

    phone_pattern = re.compile(r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}")

    # Run all queries — don't break early, collect everything
    for query in queries:
        results = await search_web(query, max_results=5)
        for result in results:
            content = result.get("content", "")
            found_emails = EMAIL_REGEX.findall(content)
            all_emails.extend(found_emails)

            found_phones = phone_pattern.findall(content)
            all_phones.extend(found_phones)

    # Filter to emails that look like they belong to this supplier
    domain = _extract_domain(supplier.website) if supplier.website else None
    if domain:
        # Prefer emails from the supplier's own domain
        domain_emails = [e for e in all_emails if domain.lower() in e.lower()]
        if domain_emails:
            all_emails = domain_emails

    emails = list({e.lower() for e in all_emails if _is_valid_email(e)})
    phones = list(set(all_phones))[:5]  # Limit phones to avoid noise

    logger.info("  Tier 5 (Google search): %d emails, %d phones", len(emails), len(phones))
    return {"emails": emails, "phones": phones, "source": "google_search"}


# ── Cheap tiers (always run both) ────────────────────────────────

CHEAP_TIERS = {"contact_page_scrape", "firecrawl_extract"}

# ── Main enrichment orchestrator ──────────────────────────────────

async def enrich_supplier_contacts(
    supplier: DiscoveredSupplier,
    aggressive: bool = True,
) -> DiscoveredSupplier:
    """Run the waterfall contact enrichment pipeline on a single supplier.

    Always runs Tiers 1 & 2 (cheap) to accumulate the best possible email.
    Only short-circuits at Tier 3+ (expensive) once a valid email is found.
    Updates the supplier's email, phone, and enrichment fields in-place.

    Args:
        supplier: The supplier to enrich.
        aggressive: If True, try all tiers including paid APIs.
                    If False, only try cheap tiers (1, 2).

    Returns:
        The supplier with updated contact info and enrichment metadata.
    """
    logger.info("Enriching contacts for: %s (website: %s)", supplier.name, supplier.website)

    result = ContactEnrichmentResult()

    # If supplier already has a good email, just validate and return
    if supplier.email and _is_valid_email(supplier.email):
        logger.info("  Supplier already has email: %s — skipping enrichment", supplier.email)
        result.best_email = supplier.email
        result.best_phone = supplier.phone
        result.enrichment_confidence = 90.0
        result.sources_tried = ["existing"]
        result.sources_succeeded = ["existing"]
        supplier.enrichment = result
        return supplier

    # Define the tier pipeline
    tiers = [
        ("contact_page_scrape", _tier1_scrape_contact_pages),
        ("firecrawl_extract", _tier2_firecrawl_extract),
    ]

    if aggressive:
        if settings.browserless_api_key:
            tiers.append(("visual_analysis", _tier3_visual_analysis))

        if settings.hunter_api_key:
            tiers.append(("hunter_io", _tier4_hunter_io))

        # Google search uses Firecrawl credits
        tiers.append(("google_search", _tier5_google_search))

    # Run the waterfall
    for tier_name, tier_fn in tiers:
        result.sources_tried.append(tier_name)

        try:
            tier_result = await tier_fn(supplier)
        except Exception as e:
            logger.warning("  Tier %s failed with exception: %s", tier_name, e)
            continue

        emails = tier_result.get("emails", [])
        phones = tier_result.get("phones", [])

        if emails:
            result.sources_succeeded.append(tier_name)
            result.emails_found.extend(emails)
        if phones:
            result.phones_found.extend(phones)

        # Cheap tiers (1 & 2): always run both to accumulate best emails.
        # Expensive tiers (3+): short-circuit once we have a valid email.
        if tier_name not in CHEAP_TIERS and result.emails_found:
            best = _pick_best_email(result.emails_found)
            if best:
                result.best_email = best
                result.enrichment_confidence = min(
                    95.0,
                    50.0 + (len(result.sources_succeeded) * 15),
                )
                logger.info(
                    "  Found email via %s: %s (confidence: %.0f) — stopping waterfall",
                    tier_name, best, result.enrichment_confidence,
                )
                break

    # After all tiers, pick the best email from everything collected
    if not result.best_email and result.emails_found:
        result.best_email = _pick_best_email(result.emails_found)
    elif result.emails_found:
        # Re-evaluate best email now that all cheap tiers have contributed
        better = _pick_best_email(result.emails_found)
        if better:
            result.best_email = better

    if result.best_email:
        result.enrichment_confidence = max(
            result.enrichment_confidence,
            min(95.0, 50.0 + (len(result.sources_succeeded) * 15)),
        )

    # Set best phone from all collected
    if result.phones_found:
        result.best_phone = result.phones_found[0]

    # Update supplier fields
    if result.best_email and not supplier.email:
        supplier.email = result.best_email
    if result.best_phone and not supplier.phone:
        supplier.phone = result.best_phone

    supplier.enrichment = result

    if result.best_email:
        logger.info(
            "  Enrichment SUCCESS for %s: email=%s, phone=%s (tried %d tiers, %d succeeded)",
            supplier.name, result.best_email, result.best_phone,
            len(result.sources_tried), len(result.sources_succeeded),
        )
    else:
        logger.warning(
            "  Enrichment FAILED for %s: no email found after trying %d tiers (%s)",
            supplier.name, len(result.sources_tried),
            ", ".join(result.sources_tried),
        )

    return supplier
