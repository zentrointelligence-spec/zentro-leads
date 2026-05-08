"""
B2C India Property Signal Scraper — RERA/social signals for new property buyers.

RERA (Real Estate Regulatory Authority) has no consolidated public API.
We detect new property buyers via:
  1. Google Custom Search — social/news posts about possession and first-home buyers
  2. 99acres.com new listings — people listing old home = just bought new one
  3. MagicBricks new project launches — builder-published buyer lists
  4. NoBroker.com — direct buyer/seller, new listings from owners = recent purchase

India-specific extra signal field:
  loan_detected: bool — home loan mention → compulsory home insurance (guaranteed sale)

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

# High-value Indian cities / micro-markets for luxury bonus
_LUXURY_AREAS = [
    "bandra", "juhu", "powai", "worli", "lower parel", "andheri",
    "koregaon park", "kalyani nagar",
    "indiranagar", "whitefield", "koramangala", "hsr layout",
    "jubilee hills", "banjara hills", "gachibowli",
    "adyar", "boat club", "alwarpet", "kilpauk",
    "south delhi", "golf course", "cyber city", "dlf",
    "new alipore", "ballygunge",
    "navrangpura", "bodakdev", "vastrapur",
]

_LANDED_KEYWORDS   = ["villa", "bungalow", "independent house", "row house", "duplex", "plot"]
_APT_KEYWORDS      = ["apartment", "flat", "bhk", "2bhk", "3bhk", "4bhk", "studio", "society", "tower"]
_LOAN_KEYWORDS     = ["home loan", "housing loan", "loan approved", "loan sanctioned", "emi"]

_IN_PHONE_RE = re.compile(r"(?:\+91|91|0)?[\s-]?[6-9]\d{9}")
_EMAIL_RE    = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_AREA_RE     = re.compile(r"(\d[\d,]*)\s*(?:sq\.?\s*ft|sqft|sq\.?\s*m|sqm)", re.IGNORECASE)


def _random_ua() -> str:
    return random.choice(_UA_POOL)


def _random_delay() -> float:
    return random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX)


def _extract_phone(text: str) -> str | None:
    m = _IN_PHONE_RE.search(text)
    return m.group(0).strip() if m else None


def _extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text)
    return m.group(0).strip() if m else None


def _extract_area(text: str) -> str | None:
    m = _AREA_RE.search(text)
    return m.group(0).strip() if m else None


def _classify_property_type(text: str) -> str:
    text_lower = text.lower()
    if any(kw in text_lower for kw in _LANDED_KEYWORDS):
        return "landed"
    return "apartment"


def _is_luxury_area(text: str) -> bool:
    text_lower = text.lower()
    return any(area in text_lower for area in _LUXURY_AREAS)


def _detect_loan(text: str) -> bool:
    """Return True if text mentions a home loan — strong insurance conversion signal."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _LOAN_KEYWORDS)


def _extract_name_from_title(title: str) -> str | None:
    if not title:
        return None
    for sep in [" - ", " — ", " | ", ": "]:
        if sep in title:
            candidate = title.split(sep)[0].strip()
            words = candidate.split()
            if 2 <= len(words) <= 4 and not any(c.isdigit() for c in candidate):
                return candidate
    return None


# ── Google Custom Search (India) ───────────────────────────────────────────────

_IN_PROPERTY_QUERIES = [
    '"new flat possession" India {year} site:facebook.com OR site:instagram.com',
    '"got possession" "new home" India {year}',
    '"first home buyer" India {year} "home loan"',
    '"keys handover" India {location} {year}',
    '"possession letter" India {year}',
    '"ghar ki chaabi" {location} {year}',
]


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
async def _google_search(query: str, num: int = 10) -> list[dict[str, Any]]:
    if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_CX:
        logger.debug("Google Custom Search not configured — skipping India property signals")
        return []

    params = {
        "key":  settings.GOOGLE_SEARCH_API_KEY,
        "cx":   settings.GOOGLE_SEARCH_CX,
        "q":    query,
        "num":  min(num, 10),
        "gl":   "in",
        "lr":   "lang_en|lang_hi",
        "dateRestrict": "m2",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(GOOGLE_SEARCH_URL, params=params)
        if resp.status_code == 429:
            logger.warning("[india_property] Google quota exceeded")
            return []
        resp.raise_for_status()
        return resp.json().get("items", [])


async def _scrape_google_india_property(
    location: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Run India property Google Custom Search queries. Never raises."""
    signals: list[dict[str, Any]] = []
    year    = str(datetime.now(timezone.utc).year)

    for tmpl in _IN_PROPERTY_QUERIES:
        if len(signals) >= limit:
            break
        query = tmpl.format(year=year, location=location)
        try:
            await asyncio.sleep(_random_delay())
            items = await _google_search(query, num=10)
            for item in items:
                snippet   = item.get("snippet", "") or ""
                title     = item.get("title", "") or ""
                full_text = f"{title} {snippet}"
                signals.append({
                    "person_name":   _extract_name_from_title(title),
                    "location":      location,
                    "property_type": _classify_property_type(full_text),
                    "property_area": _extract_area(full_text),
                    "is_luxury":     _is_luxury_area(full_text),
                    "loan_detected": _detect_loan(full_text),
                    "source_url":    item.get("link", ""),
                    "snippet":       snippet,
                    "signal_type":   "new_property",
                    "source":        "google_search_india",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(full_text),
                    "email":         _extract_email(full_text),
                })
        except Exception as exc:
            logger.warning(f"[india_property] Google query failed: {query!r} — {exc}")

    logger.info(f"[india_property] Google: {len(signals)} signals for '{location}'")
    return signals


# ── 99acres.com ────────────────────────────────────────────────────────────────

_99ACRES_URL = "https://www.99acres.com/search/property/buy/{city}"


async def _scrape_99acres_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """
    Scrape 99acres new listings.
    Sellers listing old flat often just received possession of new one.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    city_slug = location.lower().replace(" ", "-")

    try:
        await asyncio.sleep(_random_delay())
        url = _99ACRES_URL.format(city=city_slug)
        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent": _random_ua(),
                "Accept-Language": "en-IN,en;q=0.9",
            },
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.debug(f"[india_property] 99acres {resp.status_code}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["div", "article", "li"],
                class_=re.compile(r"property|listing|card|result|srpCard", re.I),
            )
            for card in cards[:limit]:
                text = card.get_text(" ", strip=True)
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "property_type": _classify_property_type(text),
                    "property_area": _extract_area(text),
                    "is_luxury":     _is_luxury_area(text),
                    "loan_detected": _detect_loan(text),
                    "source_url":    url,
                    "snippet":       text[:200],
                    "signal_type":   "new_property",
                    "source":        "99acres",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[india_property] 99acres failed for '{location}': {exc}")

    logger.info(f"[india_property] 99acres: {len(signals)} signals for '{location}'")
    return signals


# ── MagicBricks ────────────────────────────────────────────────────────────────

_MAGICBRICKS_URL = "https://www.magicbricks.com/property-for-sale/residential-real-estate"


async def _scrape_magicbricks_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """
    Scrape MagicBricks new project launches and listings.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    city_slug = location.lower().replace(" ", "-")

    try:
        await asyncio.sleep(_random_delay())
        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent": _random_ua(),
                "Accept-Language": "en-IN,en;q=0.9",
            },
            follow_redirects=True,
        ) as client:
            resp = await client.get(
                _MAGICBRICKS_URL,
                params={"proptype": "Multistorey-Apartment,Builder-Floor-Apartment,Residential-House,Villa", "cityName": location.title()},
            )
            if resp.status_code != 200:
                logger.debug(f"[india_property] MagicBricks {resp.status_code}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"card|listing|result|propCard", re.I),
            )
            for card in cards[:limit]:
                text = card.get_text(" ", strip=True)
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "property_type": _classify_property_type(text),
                    "property_area": _extract_area(text),
                    "is_luxury":     _is_luxury_area(text),
                    "loan_detected": _detect_loan(text),
                    "source_url":    _MAGICBRICKS_URL,
                    "snippet":       text[:200],
                    "signal_type":   "new_property",
                    "source":        "magicbricks",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[india_property] MagicBricks failed for '{location}': {exc}")

    logger.info(f"[india_property] MagicBricks: {len(signals)} signals for '{location}'")
    return signals


# ── NoBroker.com ───────────────────────────────────────────────────────────────

_NOBROKER_URL = "https://www.nobroker.in/property/sale/{city}/"


async def _scrape_nobroker_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """
    Scrape NoBroker direct owner listings.
    Recent buy signal — owners usually list quickly after purchase.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    city_slug = location.lower().replace(" ", "-")

    try:
        await asyncio.sleep(_random_delay())
        url = _NOBROKER_URL.format(city=city_slug)
        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent": _random_ua(),
                "Accept-Language": "en-IN,en;q=0.9",
            },
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.debug(f"[india_property] NoBroker {resp.status_code} for {url}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["div", "li"],
                class_=re.compile(r"card|listing|result|shell|nb-", re.I),
            )
            for card in cards[:limit]:
                text = card.get_text(" ", strip=True)
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "property_type": _classify_property_type(text),
                    "property_area": _extract_area(text),
                    "is_luxury":     _is_luxury_area(text),
                    "loan_detected": _detect_loan(text),
                    "source_url":    url,
                    "snippet":       text[:200],
                    "signal_type":   "new_property",
                    "source":        "nobroker",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[india_property] NoBroker failed for '{location}': {exc}")

    logger.info(f"[india_property] NoBroker: {len(signals)} signals for '{location}'")
    return signals


# ── Enrichment ─────────────────────────────────────────────────────────────────

async def enrich_india_property_lead(signal: dict[str, Any]) -> dict[str, Any]:
    """
    Best-effort enrichment from source page.
    Never raises; returns original signal on any failure.
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
                    # Re-detect loan on full page
                    if not enriched.get("loan_detected"):
                        enriched["loan_detected"] = _detect_loan(page_text)
        except Exception as exc:
            logger.debug(f"[enrich_india_property] Page fetch failed: {exc}")

    return enriched


# ── Main public function ───────────────────────────────────────────────────────

async def scrape_india_property_signals(
    location: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Aggregate India B2C property purchase signals from all available sources.

    60-day signal window — property insurance purchase window is longer than motor.

    Args:
        location: Indian city string (e.g. "Mumbai", "Bengaluru").
        limit:    Maximum signals to return.

    Returns:
        List of signal dicts. India-specific extra fields:
        loan_detected, market="india"
    """
    if not location:
        location = "India"

    per_source = max(limit // 4, 10)

    results = await asyncio.gather(
        asyncio.create_task(_scrape_google_india_property(location, per_source)),
        asyncio.create_task(_scrape_99acres_signals(location, per_source)),
        asyncio.create_task(_scrape_magicbricks_signals(location, per_source)),
        asyncio.create_task(_scrape_nobroker_signals(location, per_source)),
        return_exceptions=True,
    )

    all_signals: list[dict[str, Any]] = []
    for label, result in zip(
        ["google_search_india", "99acres", "magicbricks", "nobroker"], results
    ):
        if isinstance(result, Exception):
            logger.warning(f"[india_property] Source '{label}' raised: {result}")
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
        f"[india_property] raw={len(all_signals)} deduped={len(deduped)} "
        f"fresh={len(fresh)} for '{location}'"
    )
    return fresh[:limit]
