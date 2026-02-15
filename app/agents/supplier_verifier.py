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
    ParsedRequirements,
    SupplierVerification,
    VerificationCheck,
    VerificationResults,
)
from app.schemas.buyer_context import BuyerContext

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
    """Gather Google rating and review data as raw evidence."""
    logger.info("  ⭐ Checking Google reviews for %s", supplier.name)
    if supplier.google_rating is not None:
        return VerificationCheck(
            check_type="reviews",
            status="passed",
            score=0,  # LLM synthesis will score holistically
            details=f"Google rating: {supplier.google_rating}/5 ({supplier.google_review_count or 0} reviews)",
        )
    return VerificationCheck(
        check_type="reviews",
        status="unavailable",
        score=0,
        details="No Google reviews data available",
    )


async def _check_business_registration(supplier: DiscoveredSupplier) -> VerificationCheck:
    """Gather business registration indicators as raw evidence."""
    logger.info("  📋 Checking business registration for %s", supplier.name)
    indicators = []

    if supplier.address:
        indicators.append(f"physical address: {supplier.address}")
    if supplier.phone:
        indicators.append("phone number available")
    if supplier.email:
        indicators.append("email contact available")
    if supplier.website and supplier.website.startswith("https"):
        indicators.append("SSL-secured website")
    if supplier.certifications:
        indicators.append(f"claims certifications: {', '.join(supplier.certifications[:3])}")
    if supplier.description and len(supplier.description) > 50:
        indicators.append("detailed business description")

    return VerificationCheck(
        check_type="registration",
        status="passed" if indicators else "unavailable",
        score=0,  # LLM synthesis will score holistically
        details=f"Business indicators: {'; '.join(indicators)}" if indicators else "Limited information",
    )


async def _extract_images_if_available(supplier: DiscoveredSupplier) -> None:
    """Extract logo and product images from supplier website via Browserbase.

    Updates the supplier object in-place with logo_url and product_images.
    Returns None (not a VerificationCheck) — runs alongside verification checks
    but doesn't contribute to the composite score.
    """
    if not supplier.website:
        return None

    try:
        from app.agents.tools.image_extractor import extract_supplier_images
        image_set = await extract_supplier_images(supplier.website)

        if image_set.logo_url:
            supplier.logo_url = image_set.logo_url
        if image_set.product_images:
            supplier.product_images = image_set.product_images

        logger.info(
            "  🖼️ Images extracted for %s: logo=%s, products=%d",
            supplier.name, bool(supplier.logo_url), len(supplier.product_images),
        )
    except Exception as e:
        logger.debug("Image extraction failed for %s: %s", supplier.name, e)

    return None


async def verify_supplier(
    supplier: DiscoveredSupplier,
    index: int,
    requirements: ParsedRequirements | None = None,
    buyer_context: BuyerContext | None = None,
    priority: str = "normal",
) -> SupplierVerification:
    """Run all verification checks on a single supplier in parallel."""
    logger.info("🔎 Verifying supplier [%d]: %s", index, supplier.name)

    # ── Contact enrichment pre-step ──────────────────────────────
    # If the supplier is missing email or phone, relentlessly try to find them
    # through multiple sources before running verification checks.
    if not supplier.email or not supplier.phone:
        try:
            from app.agents.tools.contact_enricher import enrich_supplier_contacts

            supplier = await enrich_supplier_contacts(
                supplier,
                aggressive=(priority == "high"),
                priority=priority,
            )
        except Exception as e:
            logger.warning("Contact enrichment failed for %s: %s", supplier.name, e)

    checks = await asyncio.gather(
        _check_website(supplier),
        _check_google_reviews(supplier),
        _check_business_registration(supplier),
        _extract_images_if_available(supplier),
        return_exceptions=True,
    )

    valid_checks = [c for c in checks if isinstance(c, VerificationCheck)]

    # ── LLM synthesis: holistic assessment from all gathered evidence ──
    evidence_summary = {
        "supplier_name": supplier.name,
        "country": supplier.country,
        "is_intermediary": supplier.is_intermediary,
        "language_discovered": supplier.language_discovered,
        "has_email": bool(supplier.email),
        "has_phone": bool(supplier.phone),
        "has_website": bool(supplier.website),
        "checks": [
            {"check_type": c.check_type, "status": c.status, "details": c.details}
            for c in valid_checks
        ],
    }

    synthesis_prompt = f"""Assess this supplier's legitimacy based on the gathered evidence.

Supplier evidence:
{json.dumps(evidence_summary, indent=2)}

Follow your system instructions to produce a holistic assessment. Return ONLY valid JSON."""

    try:
        synthesis_resp = await call_llm_structured(
            prompt=synthesis_prompt,
            system=SYSTEM_PROMPT,
            model=settings.model_cheap,
            max_tokens=500,
        )
        text = synthesis_resp.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        synthesis = json.loads(text)
    except (json.JSONDecodeError, Exception):
        # Fallback: simple heuristic if LLM synthesis fails
        logger.warning("LLM verification synthesis failed for %s; using fallback", supplier.name)
        has_signals = sum(1 for c in valid_checks if c.status == "passed")
        synthesis = {
            "composite_score": min(100, has_signals * 35),
            "risk_level": "medium",
            "recommendation": "caution",
            "preferred_contact_method": "email" if supplier.email else ("phone" if supplier.phone else "website_form"),
            "contact_notes": None,
            "summary": "; ".join(f"{c.check_type}: {c.details}" for c in valid_checks),
        }

    # Update check scores from LLM synthesis if provided
    if "checks" in synthesis:
        llm_checks_map = {c["check_type"]: c for c in synthesis["checks"] if isinstance(c, dict)}
        for check in valid_checks:
            llm_check = llm_checks_map.get(check.check_type)
            if llm_check:
                check.score = float(llm_check.get("score", check.score))
                check.status = llm_check.get("status", check.status)
                if llm_check.get("details"):
                    check.details = llm_check["details"]

    composite = float(synthesis.get("composite_score", 0))
    risk_level = str(synthesis.get("risk_level", "medium"))
    recommendation = str(synthesis.get("recommendation", "caution"))
    preferred_contact_method = str(synthesis.get("preferred_contact_method", "email"))
    contact_notes = synthesis.get("contact_notes")
    summary = str(synthesis.get("summary", "; ".join(f"{c.check_type}: {c.details}" for c in valid_checks)))

    # Validate enum values
    if risk_level not in ("low", "medium", "high"):
        risk_level = "medium"
    if recommendation not in ("proceed", "caution", "reject"):
        recommendation = "caution"
    if preferred_contact_method not in ("email", "phone", "website_form"):
        preferred_contact_method = "email"

    logger.info("  Verification: score=%.1f, risk=%s, rec=%s, contact=%s",
                composite, risk_level, recommendation, preferred_contact_method)
    return SupplierVerification(
        supplier_name=supplier.name,
        supplier_index=index,
        checks=valid_checks,
        composite_score=round(composite, 1),
        risk_level=risk_level,
        recommendation=recommendation,
        summary=summary,
        preferred_contact_method=preferred_contact_method,
        contact_notes=contact_notes,
    )


async def verify_suppliers(
    suppliers: list[DiscoveredSupplier],
    max_concurrent: int = 5,
    requirements: ParsedRequirements | None = None,
    buyer_context: BuyerContext | None = None,
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
    
    async def _verify_with_limit(s: DiscoveredSupplier, idx: int, priority: str):
        async with semaphore:
            emit_progress("verifying", "checking_supplier",
                          f"Verifying supplier {idx + 1}/{len(suppliers)}: {s.name}...",
                          progress_pct=(idx / len(suppliers)) * 100)
            try:
                return await verify_supplier(
                    s,
                    idx,
                    requirements=requirements,
                    buyer_context=buyer_context,
                    priority=priority,
                )
            except Exception as e:
                logger.error("❌ Verification failed for supplier [%d] %s: %s", idx, s.name, e)
                # Resilience: return a structured high-risk verification instead of dropping
                # the supplier entirely. This prevents whole-stage collapse when a shared
                # dependency fails transiently.
                return SupplierVerification(
                    supplier_name=s.name,
                    supplier_index=idx,
                    checks=[
                        VerificationCheck(
                            check_type="verification_error",
                            status="failed",
                            score=0,
                            details=f"Verification process error: {str(e)[:180]}",
                        )
                    ],
                    composite_score=0.0,
                    risk_level="high",
                    recommendation="reject",
                    summary=f"Verification failed due to processing error: {str(e)[:180]}",
                    preferred_contact_method="email",
                    contact_notes="Automated checks failed; manual review required.",
                )

    tasks = []
    for i, s in enumerate(suppliers):
        if i < 5:
            priority = "high"
        elif i >= max(1, len(suppliers) // 2):
            priority = "low"
        else:
            priority = "normal"
        tasks.append(_verify_with_limit(s, i, priority))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log any exceptions that slipped through (shouldn't happen now, but safety net)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error("❌ Unexpected exception for supplier [%d]: %s", i, r)

    verifications = [r for r in results if isinstance(r, SupplierVerification)]

    # Sort by composite score descending
    verifications.sort(key=lambda v: v.composite_score, reverse=True)

    low_risk = len([v for v in verifications if v.risk_level == "low"])
    high_risk = len([v for v in verifications if v.risk_level == "high"])
    emit_progress("verifying", "complete",
                  f"Verification complete: {len(verifications)} verified. "
                  f"{low_risk} low risk, {high_risk} high risk.",
                  progress_pct=100)
    logger.info("✅ Verification complete: %d suppliers verified", len(verifications))
    return VerificationResults(verifications=verifications)
