"""
B2C India Vehicle Signal Scraper — Vaahan/social signals for new vehicle owners.

Vaahan (MoRTH) has no public API. We find newly registered vehicle owners via:
  1. Google Custom Search — Hindi/English social posts about new car deliveries
  2. CarDekho seller listings — selling 2023/24 model = just bought 2025/26
  3. Team-BHP delivery reports — India's largest car forum (public, no login)
  4. OLX India auto section — recent model year cars for sale

India-specific fields added to each signal:
  state       — Maharashtra, Karnataka, Delhi NCR, Tamil Nadu, etc.
  rto_region  — detected from city/registration number patterns (if visible)

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
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

_IN_CAR_BRANDS = [
    "Maruti", "Suzuki", "Swift", "Baleno", "Brezza", "Ertiga", "Grand Vitara",
    "Hyundai", "Creta", "Venue", "i20", "Alcazar", "Tucson",
    "Tata", "Nexon", "Punch", "Altroz", "Harrier", "Safari",
    "Mahindra", "XUV", "Scorpio", "Thar", "Bolero",
    "Honda", "City", "Amaze", "Elevate",
    "Toyota", "Fortuner", "Innova", "Urban Cruiser", "Hyryder",
    "Kia", "Seltos", "Sonet", "Carens",
    "Skoda", "Slavia", "Kushaq", "Octavia",
    "Volkswagen", "Virtus", "Taigun",
    "MG", "Hector", "Astor", "Gloster",
    "Renault", "Kwid", "Kiger", "Triber",
    "Nissan", "Magnite",
    "Royal Enfield", "Bajaj", "TVS", "Hero",  # two-wheelers
]

# Metro and Tier-1 cities with state mapping
_METRO_CITIES: dict[str, str] = {
    "mumbai":      "Maharashtra",
    "pune":        "Maharashtra",
    "nagpur":      "Maharashtra",
    "delhi":       "Delhi NCR",
    "noida":       "Delhi NCR",
    "gurgaon":     "Delhi NCR",
    "gurugram":    "Delhi NCR",
    "faridabad":   "Delhi NCR",
    "bangalore":   "Karnataka",
    "bengaluru":   "Karnataka",
    "hyderabad":   "Telangana",
    "chennai":     "Tamil Nadu",
    "coimbatore":  "Tamil Nadu",
    "kolkata":     "West Bengal",
    "ahmedabad":   "Gujarat",
    "surat":       "Gujarat",
    "jaipur":      "Rajasthan",
    "lucknow":     "Uttar Pradesh",
    "kochi":       "Kerala",
    "chandigarh":  "Punjab/Haryana",
    "bhopal":      "Madhya Pradesh",
    "indore":      "Madhya Pradesh",
    "patna":       "Bihar",
    "bhubaneswar": "Odisha",
}

# RTO region patterns (from registration number prefix in text)
_RTO_RE = re.compile(
    r"\b([A-Z]{2})[\s-]?(\d{2})[\s-]?[A-Z]{0,2}[\s-]?\d{4}\b", re.IGNORECASE
)

_IN_PHONE_RE = re.compile(r"(?:\+91|91|0)?[\s-]?[6-9]\d{9}")
_EMAIL_RE    = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


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


def _extract_vehicle_model(text: str) -> str | None:
    """Scan text for any known India car/bike brand and return the first match."""
    for brand in _IN_CAR_BRANDS:
        if brand.lower() in text.lower():
            pattern = re.compile(
                rf"\b{re.escape(brand)}\b[\s]*([\w\s]{{0,20}})",
                re.IGNORECASE,
            )
            m = pattern.search(text)
            if m:
                suffix = m.group(1).strip().split("\n")[0][:30]
                return f"{brand} {suffix}".strip() if suffix else brand
            return brand
    return None


def _extract_state(text: str, location: str) -> str | None:
    """Return Indian state from location match or RTO prefix."""
    text_lower = (text + " " + location).lower()
    for city, state in _METRO_CITIES.items():
        if city in text_lower:
            return state
    return None


def _extract_rto_region(text: str) -> str | None:
    """Extract an RTO region code if visible in text (e.g. MH 12, KA 05)."""
    m = _RTO_RE.search(text)
    return m.group(0).strip() if m else None


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

_IN_VEHICLE_QUERIES = [
    '"नई गाड़ी खरीदी" site:facebook.com OR site:instagram.com {year}',
    '"new car delivery" India {year} site:instagram.com OR site:facebook.com',
    '"just bought my new" {brand} India {year}',
    '"car delivery" India {location} {year}',
    '"new bike delivery" India {year} site:facebook.com',
]

_SAMPLE_BRANDS = ["Maruti Swift", "Tata Nexon", "Hyundai Creta", "Mahindra XUV", "Kia Seltos"]


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
async def _google_search(query: str, num: int = 10) -> list[dict[str, Any]]:
    """Call Google Custom Search API. Returns [] if not configured or quota hit."""
    if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_CX:
        logger.debug("Google Custom Search not configured — skipping India vehicle signals")
        return []

    params = {
        "key":  settings.GOOGLE_SEARCH_API_KEY,
        "cx":   settings.GOOGLE_SEARCH_CX,
        "q":    query,
        "num":  min(num, 10),
        "gl":   "in",           # Geolocation: India
        "lr":   "lang_en|lang_hi",
        "dateRestrict": "m1",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(GOOGLE_SEARCH_URL, params=params)
        if resp.status_code == 429:
            logger.warning("[india_vehicle] Google Custom Search quota exceeded")
            return []
        resp.raise_for_status()
        return resp.json().get("items", [])


async def _scrape_google_india_vehicle(
    location: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Run India vehicle Google Custom Search queries. Never raises."""
    signals: list[dict[str, Any]] = []
    year   = str(datetime.now(timezone.utc).year)
    brand  = random.choice(_SAMPLE_BRANDS)

    for tmpl in _IN_VEHICLE_QUERIES:
        if len(signals) >= limit:
            break
        query = tmpl.format(year=year, location=location, brand=brand)
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
                    "state":         _extract_state(full_text, location),
                    "rto_region":    _extract_rto_region(full_text),
                    "vehicle_model": _extract_vehicle_model(full_text),
                    "vehicle_type":  "motorcycle" if any(
                        kw in full_text.lower()
                        for kw in ("bike", "motorcycle", "royal enfield", "bajaj", "tvs", "hero")
                    ) else "car",
                    "source_url":    item.get("link", ""),
                    "snippet":       snippet,
                    "signal_type":   "new_vehicle",
                    "source":        "google_search_india",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(full_text),
                    "email":         _extract_email(full_text),
                })
        except Exception as exc:
            logger.warning(f"[india_vehicle] Google query failed: {query!r} — {exc}")

    logger.info(f"[india_vehicle] Google: {len(signals)} signals for '{location}'")
    return signals


# ── CarDekho seller listings ───────────────────────────────────────────────────

_CARDEKHO_URL = "https://www.cardekho.com/used-cars+in+{city}"


async def _scrape_cardekho_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """
    Scrape CarDekho used-car listings for 2024/2025 model vehicles.
    Seller just bought a new car → motor insurance signal.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    city_slug  = location.lower().replace(" ", "-")
    current_yr = datetime.now(timezone.utc).year
    recent_yrs = [str(current_yr), str(current_yr - 1)]

    try:
        await asyncio.sleep(_random_delay())
        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent": _random_ua(),
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            },
            follow_redirects=True,
        ) as client:
            url  = _CARDEKHO_URL.format(city=city_slug)
            resp = await client.get(url, params={"year_min": str(current_yr - 1)})
            if resp.status_code != 200:
                logger.debug(f"[india_vehicle] CarDekho {resp.status_code}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["div", "article", "li"],
                class_=re.compile(r"listing|car-item|card|result", re.I),
            )
            for card in cards[:limit]:
                text = card.get_text(" ", strip=True)
                if not any(yr in text for yr in recent_yrs):
                    continue
                model = _extract_vehicle_model(text)
                if not model:
                    continue
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "state":         _extract_state(text, location),
                    "rto_region":    _extract_rto_region(text),
                    "vehicle_model": model,
                    "vehicle_type":  "car",
                    "source_url":    url,
                    "snippet":       text[:200],
                    "signal_type":   "new_vehicle",
                    "source":        "cardekho",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[india_vehicle] CarDekho failed for '{location}': {exc}")

    logger.info(f"[india_vehicle] CarDekho: {len(signals)} signals for '{location}'")
    return signals


# ── Team-BHP delivery reports ──────────────────────────────────────────────────

_TEAMBHP_URL = "https://www.team-bhp.com/forum/official-new-car-reviews/"


async def _scrape_teambhp_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """
    Scrape Team-BHP delivery report threads (public, no login required).
    Enthusiast buyers post city + car model — premium comprehensive insurance signal.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    try:
        await asyncio.sleep(_random_delay())
        async with httpx.AsyncClient(
            timeout=25,
            headers={
                "User-Agent": _random_ua(),
                "Accept-Language": "en-IN,en;q=0.9",
                "Referer": "https://www.team-bhp.com/",
            },
            follow_redirects=True,
        ) as client:
            resp = await client.get(
                _TEAMBHP_URL,
                params={"prefixid": "7"},  # Delivery Reports prefix
            )
            if resp.status_code != 200:
                logger.debug(f"[india_vehicle] Team-BHP {resp.status_code}")
                return []

            soup    = BeautifulSoup(resp.text, "html.parser")
            threads = soup.find_all("a", title=re.compile(r"delivery|picked up|collection", re.I))

            for thread in threads[:limit]:
                title  = thread.get_text(strip=True)
                href   = thread.get("href", "")
                url    = href if href.startswith("http") else f"https://www.team-bhp.com{href}"
                model  = _extract_vehicle_model(title)
                state  = _extract_state(title, location)
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "state":         state,
                    "rto_region":    _extract_rto_region(title),
                    "vehicle_model": model,
                    "vehicle_type":  "car",
                    "source_url":    url,
                    "snippet":       title[:200],
                    "signal_type":   "new_vehicle",
                    "source":        "team_bhp",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         None,
                    "email":         None,
                })
    except Exception as exc:
        logger.warning(f"[india_vehicle] Team-BHP failed: {exc}")

    logger.info(f"[india_vehicle] Team-BHP: {len(signals)} signals for '{location}'")
    return signals


# ── OLX India auto section ─────────────────────────────────────────────────────

_OLX_URL = "https://www.olx.in/cars_c84"


async def _scrape_olx_india_signals(location: str, limit: int) -> list[dict[str, Any]]:
    """
    Scrape OLX India for recent model-year cars being sold.
    Returns [] on any failure.
    """
    signals: list[dict[str, Any]] = []
    city_slug  = location.lower().replace(" ", "_")
    current_yr = datetime.now(timezone.utc).year
    recent_yrs = [str(current_yr), str(current_yr - 1)]

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
            resp = await client.get(_OLX_URL, params={"filter": city_slug})
            if resp.status_code != 200:
                logger.debug(f"[india_vehicle] OLX {resp.status_code}")
                return []

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all(
                ["li", "div", "article"],
                class_=re.compile(r"listing|item|card|EIR5N", re.I),
            )
            for card in cards[:limit]:
                text  = card.get_text(" ", strip=True)
                if not any(yr in text for yr in recent_yrs):
                    continue
                model = _extract_vehicle_model(text)
                if not model:
                    continue
                link_tag = card.find("a")
                url = link_tag["href"] if link_tag and link_tag.get("href") else _OLX_URL
                if url.startswith("/"):
                    url = f"https://www.olx.in{url}"
                signals.append({
                    "person_name":   None,
                    "location":      location,
                    "state":         _extract_state(text, location),
                    "rto_region":    _extract_rto_region(text),
                    "vehicle_model": model,
                    "vehicle_type":  "car",
                    "source_url":    url,
                    "snippet":       text[:200],
                    "signal_type":   "new_vehicle",
                    "source":        "olx_in",
                    "market":        "india",
                    "detected_date": datetime.now(timezone.utc),
                    "phone":         _extract_phone(text),
                    "email":         _extract_email(text),
                })
    except Exception as exc:
        logger.warning(f"[india_vehicle] OLX failed for '{location}': {exc}")

    logger.info(f"[india_vehicle] OLX: {len(signals)} signals for '{location}'")
    return signals


# ── Enrichment ─────────────────────────────────────────────────────────────────

async def enrich_india_vehicle_lead(signal: dict[str, Any]) -> dict[str, Any]:
    """
    Best-effort enrichment — try to find phone/email from source page.
    Never raises; returns original signal unchanged on any failure.
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
            logger.debug(f"[enrich_india_vehicle] Page fetch failed: {exc}")

    return enriched


# ── Main public function ───────────────────────────────────────────────────────

async def scrape_india_vehicle_signals(
    location: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Aggregate India B2C vehicle purchase signals from all available sources.

    30-day signal window (motor insurance must be purchased immediately).

    Args:
        location: Indian city string (e.g. "Mumbai", "Bengaluru").
        limit:    Maximum signals to return.

    Returns:
        List of signal dicts. India-specific extra fields:
        state, rto_region, market="india"
    """
    if not location:
        location = "India"

    per_source = max(limit // 3, 10)

    results = await asyncio.gather(
        asyncio.create_task(_scrape_google_india_vehicle(location, per_source)),
        asyncio.create_task(_scrape_cardekho_signals(location, per_source)),
        asyncio.create_task(_scrape_teambhp_signals(location, per_source)),
        asyncio.create_task(_scrape_olx_india_signals(location, per_source)),
        return_exceptions=True,
    )

    all_signals: list[dict[str, Any]] = []
    for label, result in zip(
        ["google_search_india", "cardekho", "team_bhp", "olx_in"], results
    ):
        if isinstance(result, Exception):
            logger.warning(f"[india_vehicle] Source '{label}' raised: {result}")
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

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    fresh  = [
        s for s in deduped
        if not s.get("detected_date") or s["detected_date"] >= cutoff
    ]

    logger.info(
        f"[india_vehicle] raw={len(all_signals)} deduped={len(deduped)} "
        f"fresh={len(fresh)} for '{location}'"
    )
    return fresh[:limit]
