"""Verification tools — IATF portal, D&B, OpenCorporates, Google reviews."""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def check_iatf_certification(company_name: str, location: str = "") -> dict[str, Any]:
    """Check IATF 16949 certification status.

    In production, this would query the IATF Customer Portal.
    For MVP, we use web search to find certification evidence.
    """
    settings = get_settings()
    result = {
        "status": "not_checked",
        "cert_number": None,
        "scope": None,
        "expiry": None,
        "source": "iatf_portal",
    }

    try:
        # Use Firecrawl to search for IATF certification evidence
        if settings.firecrawl_api_key:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.firecrawl.dev/v1/search",
                    headers={
                        "Authorization": f"Bearer {settings.firecrawl_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": f'"{company_name}" IATF 16949 certificate',
                        "limit": 3,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("data", []):
                content = item.get("markdown", "").lower()
                if "iatf 16949" in content and (
                    "certified" in content or "certificate" in content
                ):
                    result["status"] = "evidence_found"
                    break

        if result["status"] == "not_checked":
            result["status"] = "not_found"

    except Exception:
        logger.exception("IATF check failed for: %s", company_name)
        result["status"] = "check_failed"

    return result


async def check_financial_health_dnb(company_name: str, duns_number: str | None = None) -> dict[str, Any]:
    """Check financial health via Dun & Bradstreet Direct+ API.

    Requires D&B API credentials. Returns risk assessment.
    For MVP, returns simulated structure.
    """
    result = {
        "risk_level": "unknown",
        "duns_number": duns_number,
        "paydex_score": None,
        "estimated_revenue": None,
        "employee_count": None,
        "years_in_business": None,
        "source": "dnb",
    }

    # D&B integration placeholder — requires enterprise subscription
    # In production: call D&B Direct+ REST API at https://plus.dnb.com/v1/
    logger.info("D&B check for %s — enterprise API not configured, marking as unknown", company_name)

    return result


async def check_corporate_registration(company_name: str, jurisdiction: str = "") -> dict[str, Any]:
    """Check corporate registration via OpenCorporates API."""
    result = {
        "status": "not_checked",
        "registered_name": None,
        "jurisdiction": jurisdiction,
        "incorporation_date": None,
        "source": "opencorporates",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.opencorporates.com/v0.4/companies/search",
                params={"q": company_name, "jurisdiction_code": "", "per_page": 3},
            )
            if resp.status_code == 200:
                data = resp.json()
                companies = data.get("results", {}).get("companies", [])
                if companies:
                    co = companies[0].get("company", {})
                    result["status"] = "found"
                    result["registered_name"] = co.get("name")
                    result["jurisdiction"] = co.get("jurisdiction_code")
                    result["incorporation_date"] = co.get("incorporation_date")
                else:
                    result["status"] = "not_found"
    except Exception:
        logger.exception("OpenCorporates check failed for: %s", company_name)
        result["status"] = "check_failed"

    return result


async def check_google_reviews(company_name: str, address: str = "") -> dict[str, Any]:
    """Check Google Places reviews and rating."""
    settings = get_settings()
    result = {
        "rating": None,
        "review_count": 0,
        "source": "google_places",
    }

    if not settings.google_places_api_key:
        return result

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://places.googleapis.com/v1/places:searchText",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": settings.google_places_api_key,
                    "X-Goog-FieldMask": "places.rating,places.userRatingCount",
                },
                json={"textQuery": f"{company_name} {address}", "maxResultCount": 1},
            )
            resp.raise_for_status()
            places = resp.json().get("places", [])
            if places:
                result["rating"] = places[0].get("rating")
                result["review_count"] = places[0].get("userRatingCount", 0)
    except Exception:
        logger.exception("Google reviews check failed for: %s", company_name)

    return result
