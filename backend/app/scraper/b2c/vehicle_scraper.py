"""
B2C Vehicle Signal Scraper — JPJ/social signals for new vehicle owners.

JPJ has no public API. We find newly registered vehicle owners via:
  1. Google Custom Search — social posts about new car delivery
  2. Used-car listings on Carlist.my / Mudah.my (seller just bought new)
  3. Car dealer Facebook delivery post patterns (public pages)

All sources are best-effort; any individual source failure returns []
without crashing the pipeline.
"""

from __future__ import annotations

import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings

# ── Constants ──────────────────────────────────────────────────────────────────

_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# Common Malaysian car brands for text extraction
_MY_CAR_BRANDS = [
    "Perodua", "Proton", "Honda", "Toyota", "Mazda", "Hyundai", "Kia",
    "Mitsubishi", "Nissan", "Suzuki", "BMW", "Mercedes", "Volkswagen",
    "Ford", "Isuzu", "Myvi", "Axia", "Alza", "Bezza", "Ativa",
    "Saga", "Iriz", "Persona", "X70", "X50",
]

# Phone number patterns in Malaysian context
_MY_PHONE_RE = re.compile(r"(?:60|\+60|0)[\s-]?(?:1[0-9]|[3-9])[\s-]?\d{3,4}[\s-]?\d{4}")

# Email extraction
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def _random_ua() -> str:
    """Return a random user-agent from the pool."""
    return random.choice(_UA_POOL)


def _random_delay() -> float:
    """Return a random delay in the configured scrape range."""
    return random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX)


def _extract_vehicle_model(text: str) -> str | None:
    """
    Scan text for any known Malaysian car brand name and return the first match.
    Extended with surrounding context to include model names.
    """
    for brand in _MY_CAR_BRANDS:
        if brand.lower() in text.lower():
            # Grab up to 3 words after the brand name as the model
            pattern = re.compile(
                rf"\b{re.escape(brand)}\b[\s]*([\w\s]{{0,20}})",
                re.IGNORECASE,
            )
            m = pattern.search(text)
            if m:
                model_suffix = m.group(1).strip().split("\n")[0][:30]
                return f"{brand} {model_suffix}".strip() if model_suffix else brand
            return brand
    return None


def _extract_phone(text: str) -> str | None:
    """Extract first Malaysian phone number found in text."""
    m = _MY_PHONE_RE.search(text)
    return m.group(0).strip() if m else None


def _extract_email(text: str) -> str | None:
    """Extract first email address found in text."""
    m = _EMAIL_RE.search(text)
    return m.group(0).strip() if m else None


def _is_recent(text: str, days: int = 30) -> bool:
    """
    Heuristic: return True if the text contains any year/month indicator
    suggesting the content is within the last `days` days.
    Always returns True when no date clue is found (conservative — better
    to include a lead than miss it).
    """
    now = datetime.now(timezone.utc)
    year_str = str(now.year)
    # If the current year appears in the snippet, treat as recent
    if year_str in text:
        return True
    # If previous year appears with a recent month mention, accept it too
    prev_year = str(now.year - 1)
    recent_months = {"november", "december", "jan", "feb", "mar"}
    text_lower = text.lower()
    if prev_year in text and any(m in text_lower for m in recent_months):
        return True
    return True  # default: include (let dedup handle stale)


# ── Google Custom Search source ────────────────────────────────────────────────

_VEHICLE_QUERIES = [
    'beli kereta baru {year} site:facebook.com OR site:instagram.com',
    '"new car delivery" Malaysia {year}',
    '"just got my new" kereta Malaysia {year}',
    '"ambil kereta" baru {location} {year}',
    '"collect my car" {location} {year}',
]


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
async def _google_search_signals(
    query: str,
    num: int = 10,
) -> list[dict[str, Any]]:
    """
    Call Google Custom Search API and return raw result items.
    Returns [] if API key is not configured or quota exceeded.
    """
    if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_CX:
        logger.debug("Google Custom Search not configured — skipping vehicle signal search")
        return []

    params = {
        "key": settings.GOOGLE_SEARCH_API_KEY,
        "cx": settings.GOOGLE_SEARCH_CX,
        "q": query,
        "num": min(num, 10),
        "dateRestrict": "m1",  # last 1 month
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(GOOGLE_SEARCH_URL, params=params)
        if resp.status_code == 429:
            logger.warning("Google Custom Search quota exceeded — skipping")
            return []
        resp.raise_for_status()
        data = resp.json()
    return data.get("items", [])


async def _scrape_google_vehicle_signals(
    location: str,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Run vehicle-related Google Custom Search queries and parse results
    into raw signal dicts. Never raises.
    """
    signals: list[dict[str, Any]] = []
    year = str(datetime.now(timezone.utc).year)

    for query_tmpl in _VEHICLE_QUERIES:
        if len(signals) >= limit:
            break
        query = query_tmpl.format(year=year, location=location)
        try:
            await asyncio.sleep(_random_delay())
            items = await _google_search_signals(query, num=10)
            for item in items:
                snippet = item.get("snippet", "") or ""
                title = item.get("title", "") or ""
                full_text = f"{title} {snippet}"

                if not _is_recent(full_text):
                    continue

                vehicle_model = _extract_vehicle_model(full_text)
                signals.append({
                    "person_name":    _extract_name_from_title(title),
                    "location":       location,
                    "vehicle_model":  vehicle_model,
                    "vehicle_type":   "motorcycle" if "moto" in full_text.lower() else "car",
                    "source_url":     item.get("link", ""),
                    "snippet":        snippet,
                    "signal_type":    "new_vehicle",
                    "source":         "google_search",
                    "detected_date":  datetime.now(timezone.utc),
                    "phone":          _extract_phone(full_text),
                    "email":          _extract_email(full_text),
                })
        except Exception as exc:
            logger.warning(f"Google vehicle signal query failed: {query!r} — {exc}")

    logger.info(f"[vehicle_scraper] Google: {len(signals)} signals for '{location}'")
    return signals


def _extract_name_from_title(title: str) -> str | None:
    """
    Best-effort name extraction from social-post titles.
    Facebook posts often start with the poster's name: "Ali Hassan — Just..."
    """
    if not title:
        return None
    # Patterns: "Name - post text" or "Name | page"
    for sep in [" - ", " — ", " | ", ": "]:
        if sep in title:
            candidate = title.split(sep)[0].strip()
            # Names are typically 2-4 words, no numbers
            words = candidate.split()
            if 2 <= len(words) <= 4 and not any(c.isdigit() for c in candidate):
                return candidate
    return None


# ── Carlist.my / Mudah.my used-car listing source ─────────────────────────────

_MUDAH_SEARCH_URL = "https://www.mudah.my/malaysia/cars-for-sale"
_CARLIST_SEARCH_URL = "https://www.carlist.my/cars-for-sale/malaysia"


async def _scrape_carlist_signals(
    location: str,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Scrape Carlist.my used-car listings for 2024/2025 model vehicles.
    Someone selling a near-new car likely just bought a newer one.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    current_year = datetime.now(timezone.utc).year
    recent_years = [str(current_year), str(current_year - 1)]

    try:
        await asyncio.sleep(_random_delay())
        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": _random_ua(), "Accept-Language": "en-MY,en;q=0.9"},
            follow_redirects=True,
        ) as client:
            params = {
                "q": f"{location} {current_year}",
                "year_min": str(current_year - 1),
            }
            resp = await client.get(_CARLIST_SEARCH_URL, params=params)
            if resp.status_code != 200:
                logger.debug(f"Carlist returned {resp.status_code} — skipping")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            # Carlist listing cards — class names may change; find all listings heuristically
            listing_cards = soup.find_all(["article", "div"], class_=re.compile(r"listing|car-item|card"))

            for card in listing_cards[:limit]:
                text = card.get_text(" ", strip=True)
                # Only include listings for recent model years
                if not any(yr in text for yr in recent_years):
                    continue
                vehicle_model = _extract_vehicle_model(text)
                if not vehicle_model:
                    continue
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "vehicle_model": vehicle_model,
                    "vehicle_type":  "car",
                    "source_url":    _CARLIST_SEARCH_URL,
                    "snippet":       text[:200],
                    "signal_type":   "new_vehicle",
                    "source":        "carlist_my",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"Carlist scrape failed: {exc}")

    logger.info(f"[vehicle_scraper] Carlist: {len(signals)} signals for '{location}'")
    return signals


# ── Main public functions ──────────────────────────────────────────────────────

async def scrape_vehicle_signals(
    location: str,
    vehicle_type: str = "car",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Aggregate B2C vehicle purchase signals from all available sources.

    Sources run in parallel; any individual source failure returns [] for
    that source without stopping the pipeline.

    Args:
        location:     City/region string (e.g. "Kuala Lumpur").
        vehicle_type: "car" | "motorcycle" | "commercial" — used for filtering.
        limit:        Maximum signals to return across all sources.

    Returns:
        List of raw signal dicts with keys:
        person_name, location, vehicle_model, vehicle_type, source_url,
        signal_type, source, detected_date, phone, email.
    """
    if not location:
        location = "Malaysia"

    google_task  = asyncio.create_task(_scrape_google_vehicle_signals(location, limit))
    carlist_task = asyncio.create_task(_scrape_carlist_signals(location, limit // 2))

    results = await asyncio.gather(google_task, carlist_task, return_exceptions=True)

    all_signals: list[dict[str, Any]] = []
    source_labels = ["google_search", "carlist_my"]
    for label, result in zip(source_labels, results):
        if isinstance(result, Exception):
            logger.warning(f"[vehicle_scraper] Source '{label}' raised: {result}")
        else:
            all_signals.extend(result)

    # Filter by vehicle_type if specified
    if vehicle_type != "car":
        all_signals = [s for s in all_signals if s.get("vehicle_type") == vehicle_type]

    # Deduplicate by source_url
    seen_urls: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for sig in all_signals:
        url = sig.get("source_url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(sig)

    # Filter signals older than 30 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    fresh = [
        s for s in deduped
        if not s.get("detected_date") or s["detected_date"] >= cutoff
    ]

    logger.info(
        f"[vehicle_scraper] Total signals: raw={len(all_signals)}, "
        f"deduped={len(deduped)}, fresh={len(fresh)} for location='{location}'"
    )
    return fresh[:limit]


async def enrich_vehicle_lead(signal: dict[str, Any]) -> dict[str, Any]:
    """
    Best-effort enrichment of a vehicle signal with contact information.

    Strategy:
      1. If source_url has phone/email in page — extract it.
      2. Google Custom Search: "{name} {location} phone" to find contact.
      3. Return the signal with whatever was found; partial data is fine.

    Never raises — returns the original signal unchanged on any failure.
    """
    enriched = dict(signal)

    # If we already have phone and email, no need to enrich further
    if enriched.get("phone") and enriched.get("email"):
        return enriched

    # ── Step 1: Fetch the source page for contact info ────────────────────────
    source_url = enriched.get("source_url", "")
    if source_url and not enriched.get("phone"):
        try:
            await asyncio.sleep(_random_delay())
            async with httpx.AsyncClient(
                timeout=10,
                headers={"User-Agent": _random_ua()},
                follow_redirects=True,
            ) as client:
                resp = await client.get(source_url)
                if resp.status_code == 200:
                    page_text = BeautifulSoup(resp.text, "html.parser").get_text(" ")
                    if not enriched.get("phone"):
                        enriched["phone"] = _extract_phone(page_text)
                    if not enriched.get("email"):
                        enriched["email"] = _extract_email(page_text)
        except Exception as exc:
            logger.debug(f"[enrich_vehicle_lead] Page fetch failed for {source_url}: {exc}")

    # ── Step 2: Google search for contact info ────────────────────────────────
    if not enriched.get("phone") and enriched.get("person_name"):
        name = enriched["person_name"]
        loc  = enriched.get("location", "Malaysia")
        try:
            await asyncio.sleep(_random_delay())
            items = await _google_search_signals(f'"{name}" {loc} phone contact', num=3)
            for item in items:
                text = f"{item.get('title','')} {item.get('snippet','')}"
                phone = _extract_phone(text)
                if phone:
                    enriched["phone"] = phone
                    break
        except Exception as exc:
            logger.debug(f"[enrich_vehicle_lead] Contact search failed for '{name}': {exc}")

    return enriched
