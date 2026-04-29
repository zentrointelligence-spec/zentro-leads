"""
Google Maps Places API scraper — Text Search + Place Details.
Caches results in Redis (zl:maps:*).
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.redis_client import TTL_LEADS, get_cached, set_cached


TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# Maps Google Places `types` to a human-readable industry string.
# Order matters — first match wins when iterating place types.
_PLACE_TYPE_TO_INDUSTRY: dict[str, str] = {
    "insurance_agency": "Insurance",
    "bank": "Financial Services",
    "financial_institution": "Financial Services",
    "accounting": "Accounting & Finance",
    "real_estate_agency": "Real Estate",
    "hospital": "Healthcare",
    "doctor": "Healthcare",
    "dentist": "Healthcare",
    "pharmacy": "Healthcare",
    "physiotherapist": "Healthcare",
    "school": "Education",
    "university": "Education",
    "restaurant": "Food & Beverage",
    "cafe": "Food & Beverage",
    "bakery": "Food & Beverage",
    "bar": "Food & Beverage",
    "lawyer": "Legal Services",
    "law_firm": "Legal Services",
    "car_dealer": "Automotive",
    "car_repair": "Automotive",
    "car_rental": "Automotive",
    "gym": "Fitness & Wellness",
    "beauty_salon": "Beauty & Wellness",
    "spa": "Beauty & Wellness",
    "hotel": "Hospitality",
    "lodging": "Hospitality",
    "travel_agency": "Travel & Tourism",
    "marketing_agency": "Marketing & Advertising",
    "advertising_agency": "Marketing & Advertising",
    "electrician": "Construction & Trades",
    "plumber": "Construction & Trades",
    "roofing_contractor": "Construction & Trades",
    "general_contractor": "Construction",
    "moving_company": "Logistics",
    "storage": "Logistics",
    "clothing_store": "Retail",
    "electronics_store": "Retail",
    "furniture_store": "Retail",
    "hardware_store": "Retail",
    "grocery_or_supermarket": "Retail",
    "shopping_mall": "Retail",
    "store": "Retail",
    "florist": "Retail",
    "jewelry_store": "Retail",
    "book_store": "Retail",
    "bicycle_store": "Retail",
    "shoe_store": "Retail",
}


def _infer_industry_from_types(types: list[str]) -> str | None:
    """Return the first matching industry string for a list of Google place types."""
    for t in types:
        industry = _PLACE_TYPE_TO_INDUSTRY.get(t)
        if industry:
            return industry
    return None


def _maps_cache_key(query: str, location: str) -> str:
    """Build Redis cache key fragment (zl: prefix applied by redis_client)."""
    digest = hashlib.sha256(f"{query}|{location}".encode("utf-8")).hexdigest()
    return f"maps:{digest}"


def _parse_city_country_from_components(components: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Extract city and country from Google address_components."""
    city: str | None = None
    country: str | None = None
    for comp in components or []:
        types = comp.get("types") or []
        long_name = comp.get("long_name")
        if not long_name:
            continue
        if "locality" in types:
            city = long_name
        elif "administrative_area_level_1" in types and city is None:
            city = long_name
        if "country" in types:
            country = long_name
    return city, country


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def _http_get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Perform GET and return JSON; retries on transient failures."""
    resp = await client.get(url, params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


async def scrape_google_maps(
    query: str,
    location: str,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """
    Scrape local businesses from Google Maps Places API.

    Returns list of dicts suitable for upsert into ZLCompany.
    Skips gracefully if GOOGLE_MAPS_API_KEY is empty (returns []).
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY is empty — skipping Google Maps scrape.")
        return []

    cache_key = _maps_cache_key(query, location)
    cached = await get_cached(cache_key)
    if cached is not None:
        logger.info(f"Google Maps cache hit for query={query!r} location={location!r}")
        return list(cached)

    results: list[dict[str, Any]] = []
    next_page_token: str | None = None

    async with httpx.AsyncClient() as client:
        search_query = f"{query} {location}".strip()
        params: dict[str, Any] = {
            "query": search_query,
            "key": settings.GOOGLE_MAPS_API_KEY,
        }

        while len(results) < max_results:
            if next_page_token:
                await asyncio.sleep(2.0)
                params = {
                    "pagetoken": next_page_token,
                    "key": settings.GOOGLE_MAPS_API_KEY,
                }

            data = await _http_get_json(client, TEXT_SEARCH_URL, params)
            status = data.get("status")
            if status not in ("OK", "ZERO_RESULTS"):
                logger.error(f"Google Text Search API error: status={status} body={data}")
                break

            for place in data.get("results", []):
                if len(results) >= max_results:
                    break
                place_id = place.get("place_id")
                if not place_id:
                    continue

                await asyncio.sleep(random.uniform(1.5, 3.0))

                detail_params = {
                    "place_id": place_id,
                    "fields": (
                        "name,website,formatted_phone_number,formatted_address,"
                        "rating,user_ratings_total,business_status,address_components,"
                        "geometry,types"
                    ),
                    "key": settings.GOOGLE_MAPS_API_KEY,
                }
                detail = await _http_get_json(client, PLACE_DETAILS_URL, detail_params)
                dstatus = detail.get("status")
                if dstatus != "OK":
                    logger.warning(f"Place Details failed for {place_id}: {dstatus} {detail}")
                    continue

                res = detail.get("result") or {}
                address = res.get("formatted_address")
                comps = res.get("address_components") or []
                city, country = _parse_city_country_from_components(comps)

                website = res.get("website")
                if isinstance(website, str) and website:
                    website = website.strip()

                # Combine types from Detail result and Text Search result for best coverage.
                place_types: list[str] = list(
                    dict.fromkeys(
                        (res.get("types") or []) + (place.get("types") or [])
                    )
                )
                industry = _infer_industry_from_types(place_types)

                results.append(
                    {
                        "name": res.get("name") or place.get("name") or "Unknown",
                        "website": website,
                        "phone": res.get("formatted_phone_number"),
                        "address": address,
                        "city": city,
                        "country": country,
                        "google_maps_id": place_id,
                        "google_rating": res.get("rating"),
                        "google_reviews": res.get("user_ratings_total"),
                        "latitude": (res.get("geometry") or {}).get("location", {}).get("lat"),
                        "longitude": (res.get("geometry") or {}).get("location", {}).get("lng"),
                        "industry": industry,
                        "data_source": "google_maps",
                    }
                )

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

    await set_cached(cache_key, results, ttl=TTL_LEADS)
    logger.info(f"Google Maps scrape complete: {len(results)} companies for query={query!r}")
    return results
