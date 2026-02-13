"""Agent C: Supplier Verification — verifies legitimacy via multiple checks."""

import asyncio
import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.core.progress import emit_progress
from app.agents.tools.firecrawl_scraper import scrape_website
from app.agents.tools.web_search import scrape_url_basic
from app.schemas.agent_state import (
    DiscoveredSupplier,
    SupplierVerification,
    VerificationCheck,
    VerificationResults,
)

settings = get_settings()
logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "verification.md").read_text()


async def _check_website(supplier: DiscoveredSupplier) -> VerificationCheck:
    """Scrape and analyze supplier website quality."""
    logger.info("  🌐 Checking website: %s", supplier.website or "N/A")
    if not supplier.website:
        return VerificationCheck(
            check_type="website",
            status="unavailable",
            score=0,
            details="No website URL available",
        )

    # Try Firecrawl first, fallback to basic scraping
    site_data = await scrape_website(supplier.website)
    if site_data.get("error") or not site_data.get("content"):
        site_data = await scrape_url_basic(supplier.website)

    content = site_data.get("content", "")
    if not content:
        return VerificationCheck(
            check_type="website",
            status="failed",
            score=10,
            details="Website could not be loaded or has no content",
        )

    # Use LLM to evaluate website quality
    eval_prompt = f"""Evaluate this supplier website for legitimacy and professionalism.

URL: {supplier.website}
Title: {site_data.get('title', 'N/A')}
Content (truncated): {content[:3000]}
Has SSL: {site_data.get('has_ssl', supplier.website.startswith('https'))}
Contact emails found: {site_data.get('emails', [])}
Contact phones found: {site_data.get('phones', [])}

Score 0-100 on: professional design, product information quality, company history/about page,
contact information completeness. Return JSON: {{"score": N, "details": "brief explanation"}}"""

    resp = await call_llm_structured(
        prompt=eval_prompt,
        model=settings.model_cheap,
        max_tokens=300,
    )
    try:
        data = json.loads(resp.strip().strip("`").lstrip("json\n"))
    except json.JSONDecodeError:
        data = {"score": 50, "details": "Website exists but could not fully evaluate"}

    score = float(data.get("score", 50))
    logger.info("  Website content: %d chars, score: %.0f", len(content), score)
    return VerificationCheck(
        check_type="website",
        status="passed" if score >= 60 else "failed",
        score=score,
        details=data.get("details", ""),
        raw_data=site_data,
    )


async def _check_google_reviews(supplier: DiscoveredSupplier) -> VerificationCheck:
    """Check Google rating and reviews."""
    logger.info("  ⭐ Checking Google reviews for %s", supplier.name)
    if supplier.google_rating is not None:
        score = min(100, supplier.google_rating * 20)  # 5.0 = 100
        review_bonus = min(20, (supplier.google_review_count or 0) / 5)
        score = min(100, score + review_bonus)
        return VerificationCheck(
            check_type="reviews",
            status="passed" if score >= 60 else "failed",
            score=score,
            details=f"Google rating: {supplier.google_rating}/5 ({supplier.google_review_count or 0} reviews)",
        )
    return VerificationCheck(
        check_type="reviews",
        status="unavailable",
        score=0,
        details="No Google reviews data available",
    )


async def _check_business_registration(supplier: DiscoveredSupplier) -> VerificationCheck:
    """Check business registration indicators from available data."""
    logger.info("  📋 Checking business registration for %s", supplier.name)
    indicators = []
    score = 30  # Base score: we found them, they exist

    if supplier.address:
        score += 15
        indicators.append("physical address present")
    if supplier.phone:
        score += 10
        indicators.append("phone number available")
    if supplier.email:
        score += 10
        indicators.append("email contact available")
    if supplier.website and supplier.website.startswith("https"):
        score += 10
        indicators.append("SSL-secured website")
    if supplier.certifications:
        score += 15
        indicators.append(f"claims certifications: {', '.join(supplier.certifications[:3])}")
    if supplier.description and len(supplier.description) > 50:
        score += 10
        indicators.append("detailed business description")

    score = min(100, score)
    return VerificationCheck(
        check_type="registration",
        status="passed" if score >= 60 else ("failed" if score < 40 else "unavailable"),
        score=score,
        details=f"Business indicators: {'; '.join(indicators)}" if indicators else "Limited information",
    )


async def verify_supplier(
    supplier: DiscoveredSupplier,
    index: int,
) -> SupplierVerification:
    """Run all verification checks on a single supplier in parallel."""
    logger.info("🔎 Verifying supplier [%d]: %s", index, supplier.name)

    # ── Contact enrichment pre-step ──────────────────────────────
    # If the supplier is missing email or phone, relentlessly try to find them
    # through multiple sources before running verification checks.
    if not supplier.email or not supplier.phone:
        try:
            from app.agents.tools.contact_enricher import enrich_supplier_contacts
            supplier = await enrich_supplier_contacts(supplier, aggressive=True)
        except Exception as e:
            logger.warning("Contact enrichment failed for %s: %s", supplier.name, e)

    checks = await asyncio.gather(
        _check_website(supplier),
        _check_google_reviews(supplier),
        _check_business_registration(supplier),
        return_exceptions=True,
    )

    valid_checks = [c for c in checks if isinstance(c, VerificationCheck)]

    # Calculate weighted composite score
    weights = {"website": 0.35, "reviews": 0.35, "registration": 0.30}
    total_weight = 0
    weighted_sum = 0

    for check in valid_checks:
        w = weights.get(check.check_type, 0.1)
        if check.status != "unavailable":
            weighted_sum += check.score * w
            total_weight += w

    composite = weighted_sum / total_weight if total_weight > 0 else 0

    # Penalize known intermediaries
    if supplier.is_intermediary:
        composite = max(0, composite - 15)
        logger.info("  Intermediary penalty applied: -15 points")

    # Determine risk level and recommendation
    if composite >= 70:
        risk_level, recommendation = "low", "proceed"
    elif composite >= 40:
        risk_level, recommendation = "medium", "caution"
    else:
        risk_level, recommendation = "high", "reject"

    summary_parts = [f"{c.check_type}: {c.details}" for c in valid_checks]

    # Determine preferred contact method
    preferred_contact_method = "email"
    contact_notes = None

    website_check = next((c for c in valid_checks if c.check_type == "website"), None)
    website_score = website_check.score if website_check else 0
    has_email = bool(supplier.email)
    has_phone = bool(supplier.phone)
    has_website = bool(supplier.website)
    is_non_english = supplier.language_discovered and supplier.language_discovered != "en"

    if not has_email and has_phone:
        preferred_contact_method = "phone"
        contact_notes = "No email found; phone contact recommended"
    elif website_score < 30 and has_phone:
        preferred_contact_method = "phone"
        contact_notes = "Website appears limited; phone may be more reliable"
    elif is_non_english and has_phone:
        preferred_contact_method = "phone"
        lang = supplier.language_discovered
        contact_notes = f"Website in {lang}; phone recommended for English inquiries"
    elif not has_email and not has_phone and has_website:
        preferred_contact_method = "website_form"
        contact_notes = "No direct contact info; try website contact form"

    logger.info("  Verification: score=%.1f, risk=%s, rec=%s, contact=%s",
                composite, risk_level, recommendation, preferred_contact_method)
    return SupplierVerification(
        supplier_name=supplier.name,
        supplier_index=index,
        checks=valid_checks,
        composite_score=round(composite, 1),
        risk_level=risk_level,
        recommendation=recommendation,
        summary="; ".join(summary_parts),
        preferred_contact_method=preferred_contact_method,
        contact_notes=contact_notes,
    )


async def verify_suppliers(
    suppliers: list[DiscoveredSupplier],
    max_concurrent: int = 5,
) -> VerificationResults:
    """
    Verify a batch of suppliers with concurrency control.

    Args:
        suppliers: Discovered suppliers to verify
        max_concurrent: Max concurrent verifications

    Returns:
        VerificationResults with all supplier verifications
    """
    logger.info("🔎 Starting batch verification of %d suppliers (max concurrent: %d)", len(suppliers), max_concurrent)
    emit_progress("verifying", "starting",
                  f"Verifying {len(suppliers)} suppliers (website, reviews, registration checks)...")
    semaphore = asyncio.Semaphore(max_concurrent)
    completed = 0

    async def _verify_with_limit(s: DiscoveredSupplier, idx: int):
        nonlocal completed
        async with semaphore:
            emit_progress("verifying", "checking_supplier",
                          f"Verifying supplier {idx + 1}/{len(suppliers)}: {s.name}...",
                          progress_pct=(idx / len(suppliers)) * 100)
            result = await verify_supplier(s, idx)
            completed += 1
            return result

    tasks = [_verify_with_limit(s, i) for i, s in enumerate(suppliers)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    verifications = [r for r in results if isinstance(r, SupplierVerification)]

    # Sort by composite score descending
    verifications.sort(key=lambda v: v.composite_score, reverse=True)

    logger.info("✅ Verification complete: %d suppliers verified", len(verifications))
    return VerificationResults(verifications=verifications)
