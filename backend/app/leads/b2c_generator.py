"""
B2C Lead Generator — vehicle & property life-event signals → ZLPerson + ZLLead rows.

Entry points:
  generate_b2c_vehicle_leads()         — motor insurance leads (MY or IN market-aware)
  generate_b2c_property_leads()        — home insurance leads (Malaysia)
  generate_b2c_india_property_leads()  — home insurance leads (India)
  run_b2c_vehicle_job()                — background task wrapper (vehicle, any market)
  run_b2c_property_job()               — background task wrapper (property, Malaysia)
  run_b2c_india_property_job()         — background task wrapper (property, India)

Scoring:
  calculate_b2c_score()    — unified 0-100 scorer with market + signal-type awareness
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import LeadSource, LeadTier, ZLLead, ZLPerson

# Malaysia scrapers
from app.scraper.b2c.vehicle_scraper import enrich_vehicle_lead, scrape_vehicle_signals
from app.scraper.b2c.property_scraper import enrich_property_lead, scrape_property_signals

# India scrapers
from app.scraper.b2c.india_vehicle_scraper import (
    enrich_india_vehicle_lead,
    scrape_india_vehicle_signals,
)
from app.scraper.b2c.india_property_scraper import (
    enrich_india_property_lead,
    scrape_india_property_signals,
)

# ── India metro cities (for scoring bonus) ─────────────────────────────────────

_INDIA_METROS = {
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai",
    "hyderabad", "kolkata", "pune", "ahmedabad", "surat",
    "jaipur", "lucknow", "noida", "gurgaon", "gurugram",
}


# ── Unified B2C scorer ─────────────────────────────────────────────────────────

def calculate_b2c_score(signal: dict[str, Any], icp: dict[str, Any]) -> int:
    """
    Compute a 0–100 B2C lead score.

    Base components (shared across all markets):
      Life event present   = +30
      Location match       = +20
      Age bracket match    = +20  (full credit if ICP has no range)
      Contact found        = +15  (phone or email)
      Signal recency       = +15  (window depends on event type)

    Property-specific bonuses:
      Landed property      = +10  (higher premium than apartment)
      Luxury area          = +10  (high-value property → larger premium)

    India-specific bonuses:
      Home loan detected   = +10  (compulsory home insurance = near-certain sale)
      Metro city location  = +10  (higher vehicle/property value → larger premium)
      Team-BHP source      = +5   (enthusiast buyer → comprehensive policy, not 3rd-party)
    """
    score = 0
    event  = signal.get("life_event", "")
    market = signal.get("market", "")

    # ── Life event base ──────────────────────────────────────────────────────
    if event in ("new_vehicle", "new_property", "marriage", "new_baby",
                  "job_change", "policy_lapse"):
        score += 30

    # ── Location match ───────────────────────────────────────────────────────
    signal_location = (signal.get("location") or "").lower()
    icp_locations   = [loc.lower() for loc in (icp.get("locations") or [])]
    if icp_locations:
        if any(loc in signal_location or signal_location in loc for loc in icp_locations):
            score += 20
    else:
        score += 20  # no restriction → full credit

    # ── Age bracket match ────────────────────────────────────────────────────
    signal_age     = signal.get("age")
    icp_age_ranges = icp.get("age_ranges") or []
    if not icp_age_ranges:
        score += 20
    elif signal_age:
        for bracket in icp_age_ranges:
            parts = bracket.replace(" ", "").split("-")
            if len(parts) == 2:
                try:
                    lo, hi = int(parts[0]), int(parts[1])
                    if lo <= int(signal_age) <= hi:
                        score += 20
                        break
                except (ValueError, TypeError):
                    pass
    else:
        score += 10  # unknown age → partial credit

    # ── Contact found ────────────────────────────────────────────────────────
    if signal.get("phone") or signal.get("email"):
        score += 15

    # ── Signal recency ───────────────────────────────────────────────────────
    detected: datetime | None = signal.get("detected_date")
    if detected:
        if detected.tzinfo is None:
            detected = detected.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - detected).days

        if event == "new_property":
            if days_old <= 60:
                score += 15
            elif days_old <= 90:
                score += 8
        else:
            if days_old <= 7:
                score += 15
            elif days_old <= 30:
                score += 8

    # ── Property-specific bonuses (all markets) ──────────────────────────────
    if event == "new_property":
        if signal.get("property_type") == "landed":
            score += 10
        if signal.get("is_luxury"):
            score += 10

    # ── India-specific bonuses ───────────────────────────────────────────────
    if market == "india":
        # Home loan mention → compulsory insurance → near-certain conversion
        if signal.get("loan_detected"):
            score += 10

        # Metro city → higher vehicle/property value → higher premium
        loc_lower = signal_location.lower()
        if any(metro in loc_lower for metro in _INDIA_METROS):
            score += 10

        # Team-BHP source → enthusiast buyer → comprehensive insurance
        if signal.get("source") == "team_bhp":
            score += 5

    return min(score, 100)


def _tier_from_score(score: int) -> LeadTier:
    """Map a numeric score to a LeadTier enum value."""
    if score >= 85:
        return LeadTier.HOT
    if score >= 60:
        return LeadTier.WARM
    if score >= 40:
        return LeadTier.POTENTIAL
    return LeadTier.COLD


def _tz_aware(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware (UTC)."""
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _dedup_source_url(db: AsyncSession, source_url: str) -> bool:
    """Return True if this source_url has already been stored (duplicate)."""
    if not source_url:
        return False
    result = await db.execute(
        select(ZLPerson).where(ZLPerson.linkedin_url == source_url).limit(1)
    )
    return result.scalar_one_or_none() is not None


# ── Vehicle lead generator (market-aware) ──────────────────────────────────────

async def generate_b2c_vehicle_leads(
    user_id: str,
    icp: dict[str, Any],
    db: AsyncSession,
    limit: int = 50,
) -> list[ZLLead]:
    """
    Scrape B2C vehicle purchase signals and persist as ZLPerson + ZLLead rows.

    Routes to the India scraper when icp['market'] == 'india',
    otherwise uses the Malaysia scraper.

    Args:
        user_id: Owning user UUID.
        icp:     B2C ICP dict (from /icp/build-b2c or inline).
        db:      Active async SQLAlchemy session.
        limit:   Maximum leads to create.
    """
    market   = (icp.get("market") or "malaysia").lower()
    location = (icp.get("locations") or (["India"] if market == "india" else ["Malaysia"]))[0]

    logger.info(f"[b2c_generator] Vehicle job — user={user_id} market={market} location='{location}'")

    if market == "india":
        raw_signals = await scrape_india_vehicle_signals(location=location, limit=limit * 2)
        enrich_fn   = enrich_india_vehicle_lead
    else:
        raw_signals = await scrape_vehicle_signals(location=location, vehicle_type="car", limit=limit * 2)
        enrich_fn   = enrich_vehicle_lead

    logger.info(f"[b2c_generator] Vehicle ({market}): {len(raw_signals)} raw signals")

    leads: list[ZLLead] = []

    for raw in raw_signals[:limit]:
        try:
            signal     = await enrich_fn(raw)
            source_url = signal.get("source_url") or ""

            if await _dedup_source_url(db, source_url):
                logger.debug(f"[b2c_generator] Duplicate source_url — skipping: {source_url}")
                continue

            detected = _tz_aware(signal.get("detected_date"))
            name     = signal.get("person_name") or "Unknown"

            person = ZLPerson(
                full_name    = name,
                first_name   = name.split()[0] if name != "Unknown" else None,
                last_name    = " ".join(name.split()[1:]) or None if name != "Unknown" else None,
                phone        = signal.get("phone"),
                email        = signal.get("email"),
                linkedin_url  = source_url or None,
                data_source   = LeadSource.GOOGLE_SEARCH,
                lead_type     = "b2c",
                life_event    = "new_vehicle",
                life_event_date   = detected,
                life_event_source = signal.get("source", "google_search"),
                vehicle_type  = signal.get("vehicle_type", "car"),
                vehicle_model = signal.get("vehicle_model"),
                insurance_need = "motor",
            )
            db.add(person)
            await db.flush()

            signal["life_event"] = "new_vehicle"
            score = calculate_b2c_score(signal, icp)
            tier  = _tier_from_score(score)

            vehicle_label = signal.get("vehicle_model") or "unknown vehicle"
            state_label   = signal.get("state") or ""

            intent_parts: list[str] = [f"New vehicle detected: {vehicle_label}"]
            if state_label:
                intent_parts.append(f"State: {state_label}")
            if signal.get("rto_region"):
                intent_parts.append(f"RTO: {signal['rto_region']}")

            lead = ZLLead(
                user_id       = user_id,
                person_id     = person.id,
                lead_type     = "b2c",
                insurance_type = "motor",
                market        = market,
                lead_score    = score,
                lead_tier     = tier,
                source        = LeadSource.GOOGLE_SEARCH,
                intent_signals = intent_parts,
                score_breakdown = {
                    "life_event":     30,
                    "location_match": 20 if signal.get("location") else 0,
                    "contact_found":  15 if (signal.get("phone") or signal.get("email")) else 0,
                    "metro_bonus":    10 if (market == "india" and any(
                        m in (signal.get("location") or "").lower()
                        for m in _INDIA_METROS
                    )) else 0,
                    "teambhp_bonus":  5 if signal.get("source") == "team_bhp" else 0,
                    "signal_recency": max(0, score - 75),
                },
                icp_match_score     = min(score, 100),
                recommended_product = "Motor Insurance",
            )
            db.add(lead)
            leads.append(lead)

            logger.debug(
                f"[b2c_generator] Vehicle lead ({market}): '{name}' "
                f"vehicle='{vehicle_label}' score={score}"
            )
        except Exception as exc:
            logger.error(f"[b2c_generator] Vehicle lead failed: {exc}")
            continue

    logger.info(f"[b2c_generator] Created {len(leads)} vehicle leads for user={user_id}")
    return leads


# ── Malaysia property lead generator ──────────────────────────────────────────

async def generate_b2c_property_leads(
    user_id: str,
    icp: dict[str, Any],
    db: AsyncSession,
    limit: int = 50,
) -> list[ZLLead]:
    """
    Scrape Malaysia B2C property purchase signals and persist as ZLPerson + ZLLead rows.

    life_event      = "new_property"
    insurance_need  = "home"
    life_event_source = "napic" | "propertyguru" | "iproperty" | "mudah_my" | "google_search"
    """
    location = (icp.get("locations") or ["Malaysia"])[0]
    logger.info(f"[b2c_generator] Property (MY) job — user={user_id} location='{location}'")

    raw_signals = await scrape_property_signals(location=location, property_type="residential", limit=limit * 2)
    logger.info(f"[b2c_generator] Property (MY): {len(raw_signals)} raw signals")

    leads: list[ZLLead] = []

    for raw in raw_signals[:limit]:
        try:
            signal     = await enrich_property_lead(raw)
            source_url = signal.get("source_url") or ""

            if await _dedup_source_url(db, source_url):
                logger.debug(f"[b2c_generator] Duplicate MY property source_url — skipping")
                continue

            detected = _tz_aware(signal.get("detected_date"))
            name     = signal.get("person_name") or "Unknown"

            person = ZLPerson(
                full_name    = name,
                first_name   = name.split()[0] if name != "Unknown" else None,
                last_name    = " ".join(name.split()[1:]) or None if name != "Unknown" else None,
                phone        = signal.get("phone"),
                email        = signal.get("email"),
                linkedin_url  = source_url or None,
                data_source   = LeadSource.GOOGLE_SEARCH,
                lead_type     = "b2c",
                life_event    = "new_property",
                life_event_date    = detected,
                life_event_source  = signal.get("source", "napic"),
                property_type      = signal.get("property_type", "apartment"),
                insurance_need     = "home",
            )
            db.add(person)
            await db.flush()

            signal["life_event"] = "new_property"
            score = calculate_b2c_score(signal, icp)
            tier  = _tier_from_score(score)

            prop_label  = signal.get("property_type", "property")
            area_label  = signal.get("property_area") or ""
            signal_text = f"New property: {prop_label}"
            if area_label:
                signal_text += f" ({area_label})"
            if signal.get("is_luxury"):
                signal_text += " — luxury area"

            lead = ZLLead(
                user_id       = user_id,
                person_id     = person.id,
                lead_type     = "b2c",
                insurance_type = "home",
                market        = "malaysia",
                lead_score    = score,
                lead_tier     = tier,
                source        = LeadSource.GOOGLE_SEARCH,
                intent_signals = [signal_text],
                score_breakdown = {
                    "life_event":     30,
                    "location_match": 20 if signal.get("location") else 0,
                    "contact_found":  15 if (signal.get("phone") or signal.get("email")) else 0,
                    "property_bonus": (10 if signal.get("property_type") == "landed" else 0)
                                    + (10 if signal.get("is_luxury") else 0),
                    "signal_recency": max(0, score - 75),
                },
                icp_match_score     = min(score, 100),
                recommended_product = "Home/Fire Insurance",
            )
            db.add(lead)
            leads.append(lead)

            logger.debug(
                f"[b2c_generator] Property (MY): '{name}' type='{prop_label}' score={score}"
            )
        except Exception as exc:
            logger.error(f"[b2c_generator] Property (MY) lead failed: {exc}")
            continue

    logger.info(f"[b2c_generator] Created {len(leads)} MY property leads for user={user_id}")
    return leads


# ── India property lead generator ─────────────────────────────────────────────

async def generate_b2c_india_property_leads(
    user_id: str,
    icp: dict[str, Any],
    db: AsyncSession,
    limit: int = 50,
) -> list[ZLLead]:
    """
    Scrape India B2C property purchase signals and persist as ZLPerson + ZLLead rows.

    life_event       = "new_property"
    insurance_need   = "home"
    life_event_source = "99acres" | "magicbricks" | "nobroker" | "google_search_india"
    Extra field: loan_detected → +10 score (compulsory home insurance = near-certain sale)
    """
    location = (icp.get("locations") or ["Mumbai"])[0]
    logger.info(f"[b2c_generator] Property (IN) job — user={user_id} location='{location}'")

    raw_signals = await scrape_india_property_signals(location=location, limit=limit * 2)
    logger.info(f"[b2c_generator] Property (IN): {len(raw_signals)} raw signals")

    leads: list[ZLLead] = []

    for raw in raw_signals[:limit]:
        try:
            signal     = await enrich_india_property_lead(raw)
            source_url = signal.get("source_url") or ""

            if await _dedup_source_url(db, source_url):
                logger.debug(f"[b2c_generator] Duplicate IN property source_url — skipping")
                continue

            detected = _tz_aware(signal.get("detected_date"))
            name     = signal.get("person_name") or "Unknown"

            person = ZLPerson(
                full_name    = name,
                first_name   = name.split()[0] if name != "Unknown" else None,
                last_name    = " ".join(name.split()[1:]) or None if name != "Unknown" else None,
                phone        = signal.get("phone"),
                email        = signal.get("email"),
                linkedin_url  = source_url or None,
                data_source   = LeadSource.GOOGLE_SEARCH,
                lead_type     = "b2c",
                life_event    = "new_property",
                life_event_date    = detected,
                life_event_source  = signal.get("source", "99acres"),
                property_type      = signal.get("property_type", "apartment"),
                insurance_need     = "home",
            )
            db.add(person)
            await db.flush()

            signal["life_event"]  = "new_property"
            signal["market"]      = "india"
            score = calculate_b2c_score(signal, icp)
            tier  = _tier_from_score(score)

            prop_label  = signal.get("property_type", "property")
            area_label  = signal.get("property_area") or ""
            signal_text = f"New property: {prop_label}"
            if area_label:
                signal_text += f" ({area_label})"
            if signal.get("is_luxury"):
                signal_text += " — luxury area"
            if signal.get("loan_detected"):
                signal_text += " — home loan detected"

            loan_bonus = 10 if signal.get("loan_detected") else 0
            is_metro   = any(m in (signal.get("location") or "").lower() for m in _INDIA_METROS)

            lead = ZLLead(
                user_id       = user_id,
                person_id     = person.id,
                lead_type     = "b2c",
                insurance_type = "home",
                market        = "india",
                lead_score    = score,
                lead_tier     = tier,
                source        = LeadSource.GOOGLE_SEARCH,
                intent_signals = [signal_text],
                score_breakdown = {
                    "life_event":     30,
                    "location_match": 20 if signal.get("location") else 0,
                    "contact_found":  15 if (signal.get("phone") or signal.get("email")) else 0,
                    "property_bonus": (10 if signal.get("property_type") == "landed" else 0)
                                    + (10 if signal.get("is_luxury") else 0),
                    "loan_bonus":     loan_bonus,
                    "metro_bonus":    10 if is_metro else 0,
                    "signal_recency": max(0, score - 85),
                },
                icp_match_score     = min(score, 100),
                recommended_product = "Home/Fire Insurance",
            )
            db.add(lead)
            leads.append(lead)

            logger.debug(
                f"[b2c_generator] Property (IN): '{name}' type='{prop_label}' "
                f"loan={signal.get('loan_detected')} metro={is_metro} score={score}"
            )
        except Exception as exc:
            logger.error(f"[b2c_generator] Property (IN) lead failed: {exc}")
            continue

    logger.info(f"[b2c_generator] Created {len(leads)} IN property leads for user={user_id}")
    return leads


# ── Background job wrappers ────────────────────────────────────────────────────

async def run_b2c_vehicle_job(
    user_id: str,
    icp: dict[str, Any],
    limit: int = 50,
) -> None:
    """Standalone background task — vehicle (market-aware). Creates own DB session."""
    market = (icp.get("market") or "malaysia").lower()
    logger.info(f"[b2c_generator] Vehicle background job ({market}) — user={user_id}")
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                leads = await generate_b2c_vehicle_leads(user_id=user_id, icp=icp, db=db, limit=limit)
        logger.info(f"[b2c_generator] Vehicle job done — {len(leads)} leads for user={user_id}")
    except Exception as exc:
        logger.error(f"[b2c_generator] Vehicle job failed for user={user_id}: {exc}")


async def run_b2c_property_job(
    user_id: str,
    icp: dict[str, Any],
    limit: int = 50,
) -> None:
    """Standalone background task — Malaysia property. Creates own DB session."""
    logger.info(f"[b2c_generator] Property (MY) background job — user={user_id}")
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                leads = await generate_b2c_property_leads(user_id=user_id, icp=icp, db=db, limit=limit)
        logger.info(f"[b2c_generator] Property (MY) job done — {len(leads)} leads for user={user_id}")
    except Exception as exc:
        logger.error(f"[b2c_generator] Property (MY) job failed for user={user_id}: {exc}")


async def run_b2c_india_property_job(
    user_id: str,
    icp: dict[str, Any],
    limit: int = 50,
) -> None:
    """Standalone background task — India property. Creates own DB session."""
    logger.info(f"[b2c_generator] Property (IN) background job — user={user_id}")
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                leads = await generate_b2c_india_property_leads(user_id=user_id, icp=icp, db=db, limit=limit)
        logger.info(f"[b2c_generator] Property (IN) job done — {len(leads)} leads for user={user_id}")
    except Exception as exc:
        logger.error(f"[b2c_generator] Property (IN) job failed for user={user_id}: {exc}")
