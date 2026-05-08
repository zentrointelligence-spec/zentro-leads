"""
B2C Property Transaction Signal Scraper — NAPIC/social signals for new property buyers.

NAPIC (National Property Information Centre) has no public API.
We detect new property buyers via:
  1. Google Custom Search — social posts about key collection, first home
  2. PropertyGuru Malaysia — new listings (seller just bought replacement property)
  3. iProperty.com.my — new development project buyer announcements
  4. Mudah.my property section — new private-seller listings

All sources are best-effort; any individual source failure returns []
without crashing the pipeline.

60-day signal window (property insurance purchase window is longer than motor).
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

# High-value landed areas — presence → luxury bonus in scoring
_LUXURY_AREAS = [
    "damansara", "mont kiara", "bangsar", "sri hartamas", "bukit tunku",
    "petaling jaya", "subang", "ampang", "setapak", "cheras", "puchong",
    "sunway", "cyberjaya", "putrajaya", "iskandar", "medini", "bukit jalil",
    "desa park", "segambut", "kota damansara", "ara damansara",
    "brickfields", "klcc", "kenny hills", "country heights",
]

_LANDED_KEYWORDS = [
    "bungalow", "semi-d", "semi detached", "terrace", "link house",
    "townhouse", "villa", "cluster", "landed",
]

_APARTMENT_KEYWORDS = [
    "apartment", "condo", "condominium", "serviced residence",
    "flat", "studio", "soho", "suites", "residences",
]

_MY_PHONE_RE = re.compile(r"(?:60|\+60|0)[\s-]?(?:1[0-9]|[3-9])[\s-]?\d{3,4}[\s-]?\d{4}")
_EMAIL_RE    = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_AREA_RE     = re.compile(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|sq\.?\s*m|sqm)", re.IGNORECASE)


def _random_ua() -> str:
    return random.choice(_UA_POOL)


def _random_delay() -> float:
    return random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX)


def _extract_phone(text: str) -> str | None:
    m = _MY_PHONE_RE.search(text)
    return m.group(0).strip() if m else None


def _extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text)
    return m.group(0).strip() if m else None


def _extract_area(text: str) -> str | None:
    """Extract the first floor area mention from text."""
    m = _AREA_RE.search(text)
    return m.group(0).strip() if m else None


def _classify_property_type(text: str) -> str:
    """Return 'landed' | 'apartment' based on keyword presence."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in _LANDED_KEYWORDS):
        return "landed"
    if any(kw in text_lower for kw in _APARTMENT_KEYWORDS):
        return "apartment"
    return "apartment"


def _is_luxury_area(text: str) -> bool:
    """Return True if text mentions a known high-value Malaysian area."""
    text_lower = text.lower()
    return any(area in text_lower for area in _LUXURY_AREAS)


def _extract_name_from_title(title: str) -> str | None:
    """Best-effort person name from a social post title."""
    if not title:
        return None
    for sep in [" - ", " — ", " | ", ": "]:
        if sep in title:
            candidate = title.split(sep)[0].strip()
            words = candidate.split()
            if 2 <= len(words) <= 4 and not any(c.isdigit() for c in candidate):
                return candidate
    return None


# ── Google Custom Search ───────────────────────────────────────────────────────

_PROPERTY_QUERIES = [
    '"beli rumah baru" {location} {year} site:facebook.com OR site:instagram.com',
    '"new home keys collection" Malaysia {year}',
    '"first home buyer" {location} {year}',
    '"ambil kunci" rumah {location} {year}',
    '"SPA signing" {location} {year} property',
    '"move in" new home {location} {year}',
]


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
async def _google_search(query: str, num: int = 10) -> list[dict[str, Any]]:
    """Call Google Custom Search. Returns [] if not configured or quota hit."""
    if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_CX:
        logger.debug("Google Custom Search not configured — skipping property signals")
        return []

    params = {
        "key": settings.GOOGLE_SEARCH_API_KEY,
        "cx":  settings.GOOGLE_SEARCH_CX,
        "q":   query,
        "num": min(num, 10),
        "dateRestrict": "m2",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(GOOGLE_SEARCH_URL, params=params)
        if resp.status_code == 429:
            logger.warning("Google Custom Search quota exceeded")
            return []
        resp.raise_for_status()
        return resp.json().get("items", [])


async def _scrape_google_property_signals(
    location: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Run property-related Google Custom Search queries. Never raises."""
    signals: list[dict[str, Any]] = []
    year = str(datetime.now(timezone.utc).year)

    for query_tmpl in _PROPERTY_QUERIES:
        if len(signals) >= limit:
            break
        query = query_tmpl.format(year=year, location=location)
        try:
            await asyncio.sleep(_random_delay())
            items = await _google_search(query, num=10)
            for item in items:
                snippet   = item.get("snippet", "") or ""
                title     = item.get("title", "") or ""
                full_text = f"{title} {snippet}"

                signals.append({
                    "person_name":    _extract_name_from_title(title),
                    "location":       location,
                    "property_type":  _classify_property_type(full_text),
                    "property_area":  _extract_area(full_text),
                    "is_luxury":      _is_luxury_area(full_text),
                    "source_url":     item.get("link", ""),
                    "snippet":        snippet,
                    "signal_type":    "new_property",
                    "source":         "google_search",
                    "detected_date":  datetime.now(timezone.utc),
                    "phone":          _extract_phone(full_text),
                    "email":          _extract_email(full_text),
                })
        except Exception as exc:
            logger.warning(f"[property_scraper] Google query failed: {query!r} — {exc}")

    logger.info(f"[property_scraper] Google: {len(signals)} signals for '{location}'")
    return signals


# ── PropertyGuru Malaysia ──────────────────────────────────────────────────────

_PROPERTYGURU_URL = "https://www.propertyguru.com.my/property-for-sale"


async def _scrape_propertyguru_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """
    Scrape PropertyGuru new listings.
    People listing for sale often just bought a larger property → need home insurance.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    try:
        await asyncio.sleep(_random_delay())
        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent": _random_ua(),
                "Accept-Language": "en-MY,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            follow_redirects=True,
        ) as client:
            resp = await client.get(
                _PROPERTYGURU_URL,
                params={"market": "residential", "region_code": "MY", "search": location},
            )
            if resp.status_code != 200:
                logger.debug(f"[property_scraper] PropertyGuru {resp.status_code}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["div", "article", "li"],
                class_=re.compile(r"listing|property-card|PropertyCard|result", re.I),
            )
            for card in cards[:limit]:
                text = card.get_text(" ", strip=True)
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "property_type": _classify_property_type(text),
                    "property_area": _extract_area(text),
                    "is_luxury":     _is_luxury_area(text),
                    "source_url":    _PROPERTYGURU_URL,
                    "snippet":       text[:200],
                    "signal_type":   "new_property",
                    "source":        "propertyguru",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[property_scraper] PropertyGuru failed: {exc}")

    logger.info(f"[property_scraper] PropertyGuru: {len(signals)} signals for '{location}'")
    return signals


# ── iProperty.com.my ──────────────────────────────────────────────────────────

_IPROPERTY_URL = "https://www.iproperty.com.my/sale/"


async def _scrape_iproperty_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """Scrape iProperty new/development listings. Returns [] on any failure."""
    signals: list[dict[str, Any]] = []
    try:
        await asyncio.sleep(_random_delay())
        location_slug = location.lower().replace(" ", "-")
        url = f"{_IPROPERTY_URL}{location_slug}/"
        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": _random_ua(), "Accept-Language": "en-MY,en;q=0.9"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.debug(f"[property_scraper] iProperty {resp.status_code} for {url}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"listing|property|card|result", re.I),
            )
            for card in cards[:limit]:
                text = card.get_text(" ", strip=True)
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "property_type": _classify_property_type(text),
                    "property_area": _extract_area(text),
                    "is_luxury":     _is_luxury_area(text),
                    "source_url":    url,
                    "snippet":       text[:200],
                    "signal_type":   "new_property",
                    "source":        "iproperty",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[property_scraper] iProperty failed for '{location}': {exc}")

    logger.info(f"[property_scraper] iProperty: {len(signals)} signals for '{location}'")
    return signals


# ── Mudah.my property ─────────────────────────────────────────────────────────

_MUDAH_PROPERTY_URL = "https://www.mudah.my/malaysia/properties-for-sale"


async def _scrape_mudah_property_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """Scrape Mudah.my property listings. Returns [] on any failure."""
    signals: list[dict[str, Any]] = []
    try:
        await asyncio.sleep(_random_delay())
        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": _random_ua(), "Accept-Language": "en-MY,en;q=0.9"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(_MUDAH_PROPERTY_URL, params={"q": location, "sort": "date"})
            if resp.status_code != 200:
                logger.debug(f"[property_scraper] Mudah {resp.status_code}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["div", "li", "article"],
                class_=re.compile(r"listing|item|card|ad-", re.I),
            )
            for card in cards[:limit]:
                text = card.get_text(" ", strip=True)
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "property_type": _classify_property_type(text),
                    "property_area": _extract_area(text),
                    "is_luxury":     _is_luxury_area(text),
                    "source_url":    _MUDAH_PROPERTY_URL,
                    "snippet":       text[:200],
                    "signal_type":   "new_property",
                    "source":        "mudah_my",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[property_scraper] Mudah failed: {exc}")

    logger.info(f"[property_scraper] Mudah: {len(signals)} signals for '{location}'")
    return signals


# ── Enrichment ─────────────────────────────────────────────────────────────────

async def enrich_property_lead(signal: dict[str, Any]) -> dict[str, Any]:
    """
    Best-effort enrichment — try to find phone/email on the source page.
    Never raises; returns the original signal unchanged on failure.
    """
    enriched = dict(signal)
    if enriched.get("phone") and enriched.get("email"):
        return enriched

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
                    enriched["phone"] = enriched.get("phone") or _extract_phone(page_text)
                    enriched["email"] = enriched.get("email") or _extract_email(page_text)
        except Exception as exc:
            logger.debug(f"[enrich_property_lead] Page fetch failed for {source_url}: {exc}")

    return enriched


# ── Main public function ───────────────────────────────────────────────────────

async def scrape_property_signals(
    location: str,
    property_type: str = "residential",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Aggregate B2C property purchase signals from all available sources.

    60-day signal window — property insurance purchase window is longer than motor.

    Args:
        location:      City/region string (e.g. "Kuala Lumpur").
        property_type: "residential" | "commercial" for future filtering.
        limit:         Maximum signals to return.

    Returns:
        List of signal dicts with keys:
        person_name, location, property_type, property_area, is_luxury,
        source_url, signal_type, source, detected_date, phone, email.
    """
    if not location:
        location = "Malaysia"

    per_source = max(limit // 3, 10)

    results = await asyncio.gather(
        asyncio.create_task(_scrape_google_property_signals(location, per_source)),
        asyncio.create_task(_scrape_propertyguru_signals(location, per_source)),
        asyncio.create_task(_scrape_iproperty_signals(location, per_source)),
        asyncio.create_task(_scrape_mudah_property_signals(location, per_source)),
        return_exceptions=True,
    )

    all_signals: list[dict[str, Any]] = []
    for label, result in zip(
        ["google_search", "propertyguru", "iproperty", "mudah_my"], results
    ):
        if isinstance(result, Exception):
            logger.warning(f"[property_scraper] Source '{label}' raised: {result}")
        else:
            all_signals.extend(result)

    # Deduplicate by source_url
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for sig in all_signals:
        url = sig.get("source_url", "")
        if url and url in seen:
            continue
        seen.add(url)
        deduped.append(sig)

    # 60-day freshness window
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    fresh  = [
        s for s in deduped
        if not s.get("detected_date") or s["detected_date"] >= cutoff
    ]

    logger.info(
        f"[property_scraper] raw={len(all_signals)} deduped={len(deduped)} "
        f"fresh={len(fresh)} for '{location}'"
    )
    return fresh[:limit]
