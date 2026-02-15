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

    Status values:
    - evidence_found: Web evidence of active IATF certification found
    - not_found: Search ran successfully but no certification evidence found
    - data_unavailable: Could not perform the check (API error, timeout, no key)
    """
    settings = get_settings()
    result = {
        "status": "data_unavailable",
        "cert_number": None,
        "scope": None,
        "expiry": None,
        "source": "iatf_portal",
        "note": "",
    }

    try:
        if not settings.firecrawl_api_key:
            result["note"] = "Firecrawl API key not configured — unable to verify"
            return result

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

        found = False
        for item in data.get("data", []):
            content = item.get("markdown", "").lower()
            if "iatf 16949" in content and (
                "certified" in content or "certificate" in content
            ):
                found = True
                break

        if found:
            result["status"] = "evidence_found"
            result["note"] = "Web search found evidence of IATF 16949 certification"
        else:
            result["status"] = "not_found"
            result["note"] = "Search completed but no IATF certification evidence found online"

    except Exception:
        logger.exception("IATF check failed for: %s", company_name)
        result["status"] = "data_unavailable"
        result["note"] = "Verification service error — could not check, NOT a negative result"

    return result


async def check_financial_health_dnb(company_name: str, duns_number: str | None = None) -> dict[str, Any]:
    """Check financial health via Dun & Bradstreet Direct+ API.

    Requires D&B API credentials. Returns risk assessment.
    For MVP, returns simulated structure.

    Status: data_unavailable when API not configured (NOT a negative signal).
    """
    result = {
        "risk_level": "data_unavailable",
        "duns_number": duns_number,
        "paydex_score": None,
        "estimated_revenue": None,
        "employee_count": None,
        "years_in_business": None,
        "source": "dnb",
        "note": "D&B enterprise API not configured — financial data unavailable, NOT a negative signal",
    }

    # D&B integration placeholder — requires enterprise subscription
    # In production: call D&B Direct+ REST API at https://plus.dnb.com/v1/
    logger.info("D&B check for %s — enterprise API not configured, marking as data_unavailable", company_name)

    return result


async def check_corporate_registration(company_name: str, jurisdiction: str = "") -> dict[str, Any]:
    """Check corporate registration via OpenCorporates API.

    Status values:
    - found: Company found in corporate registry
    - not_found: Search ran but company not found (may just be different name)
    - data_unavailable: API error, timeout, or service down — NOT a negative result
    """
    result = {
        "status": "data_unavailable",
        "registered_name": None,
        "jurisdiction": jurisdiction,
        "incorporation_date": None,
        "source": "opencorporates",
        "note": "",
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
                    result["note"] = "Corporate registration confirmed"
                else:
                    result["status"] = "not_found"
                    result["note"] = "Not found in OpenCorporates — may use a different registered name"
            else:
                result["note"] = f"OpenCorporates returned HTTP {resp.status_code} — could not verify"
    except Exception:
        logger.exception("OpenCorporates check failed for: %s", company_name)
        result["status"] = "data_unavailable"
        result["note"] = "Corporate registry check failed (timeout/error) — NOT a negative result"

    return result


async def check_google_reviews(company_name: str, address: str = "") -> dict[str, Any]:
    """Check Google Places reviews and rating.

    Returns rating/review_count when available.
    note field explains data availability.
    """
    settings = get_settings()
    result = {
        "rating": None,
        "review_count": 0,
        "source": "google_places",
        "note": "",
    }

    if not settings.google_places_api_key:
        result["note"] = "Google Places API not configured — review data unavailable"
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
                result["note"] = "Google reviews data retrieved"
            else:
                result["note"] = "No Google Places listing found"
    except Exception:
        logger.exception("Google reviews check failed for: %s", company_name)
        result["note"] = "Google Places check failed (timeout/error) — review data unavailable"

    return result
