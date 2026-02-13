"""Google Places API tool for local manufacturer discovery."""

import httpx
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


async def search_google_places(
    query: str,
    location_bias: str | None = None,
    max_results: int = 10,
    language_code: str | None = None,
) -> list[dict]:
    """
    Search Google Places for manufacturers/suppliers.

    Args:
        query: Search query, e.g. "canvas tote bag manufacturer Los Angeles"
        location_bias: City/state for location weighting
        max_results: Maximum results to return (max 20)
        language_code: ISO language code (e.g. "zh", "tr", "vi"). Defaults to "en".

    Returns:
        List of place dicts with name, address, phone, website, rating, etc.
    """
    logger.info("  Google Places query: '%s' (lang=%s)", query, language_code or "en")
    if not settings.google_places_api_key:
        logger.warning("  Google Places API key not configured, skipping")
        return []

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_places_api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
            "places.websiteUri,places.rating,places.userRatingCount,"
            "places.businessStatus,places.types,places.shortFormattedAddress,"
            "places.primaryType,places.editorialSummary"
        ),
    }

    body: dict = {
        "textQuery": query,
        "maxResultCount": min(max_results, 20),
        "languageCode": language_code or "en",
    }

    # If a location bias is provided, append it to the query for geo-relevance
    if location_bias and location_bias.lower() not in query.lower():
        body["textQuery"] = f"{query} {location_bias}"
        logger.info("  Applied location bias: '%s' → '%s'", query, body["textQuery"])

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, Exception) as e:
            logger.error("  Google Places search failed: %s", e)
            return []

    results = []
    for place in data.get("places", []):
        results.append({
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
            "phone": place.get("nationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "rating": place.get("rating"),
            "review_count": place.get("userRatingCount"),
            "business_status": place.get("businessStatus"),
            "types": place.get("types", []),
            "description": place.get("editorialSummary", {}).get("text"),
            "source": "google_places",
        })

    logger.info("  Google Places: %d results for '%s'", len(results), query[:50])
    return results
