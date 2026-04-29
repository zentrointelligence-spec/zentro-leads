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
                        "rating,user_ratings_total,business_status,address_components,geometry"
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
                        "data_source": "google_maps",
                    }
                )

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

    await set_cached(cache_key, results, ttl=TTL_LEADS)
    logger.info(f"Google Maps scrape complete: {len(results)} companies for query={query!r}")
    return results
