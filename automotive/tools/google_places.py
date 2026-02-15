"""Google Places API tool for geographic supplier discovery."""

import logging
import uuid

import httpx

from app.core.config import get_settings
from automotive.schemas.discovery import DiscoveredSupplier

logger = logging.getLogger(__name__)


async def search_google_places(query: str) -> list[DiscoveredSupplier]:
    """Search Google Places Text Search for manufacturers matching the query."""
    settings = get_settings()
    if not settings.google_places_api_key:
        logger.warning("Google Places API key not configured, skipping")
        return []

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_places_api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
            "places.websiteUri,places.rating,places.userRatingCount,places.types,"
            "places.businessStatus"
        ),
    }
    body = {"textQuery": query, "maxResultCount": 20}

    suppliers = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        for place in data.get("places", []):
            if place.get("businessStatus") != "OPERATIONAL":
                continue

            name = place.get("displayName", {}).get("text", "")
            if not name:
                continue

            suppliers.append(DiscoveredSupplier(
                supplier_id=str(uuid.uuid4()),
                company_name=name,
                headquarters=place.get("formattedAddress", ""),
                website=place.get("websiteUri"),
                phone=place.get("nationalPhoneNumber"),
                sources=["google_places"],
                data_richness=40 if place.get("websiteUri") else 20,
            ))

        logger.info("Google Places returned %d results for: %s", len(suppliers), query)
    except Exception:
        logger.exception("Google Places search failed for: %s", query)

    return suppliers
