"""
Lead generation orchestrator — scrape, enrich, verify, score, persist, ZIMS sync.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.email.verifier import find_best_email, find_role_email
from app.models import (
    LeadSource,
    LeadTier,
    ZLCompany,
    ZLICP,
    ZLLead,
    ZLPerson,
    ZLSuppressionList,
    ZLUser,
)
from app.scraper.google_maps.scraper import scrape_google_maps
from app.scraper.website.scraper import scrape_company_website
from app.analytics.tracker import track_lead_generated
from app.intent.engine import enrich_company_intent
from app.intent.rss_monitor import scan_all_rss_feeds
from app.scoring.engine import (
    _infer_seniority_from_title,
    calculate_lead_score,
    generate_ai_outreach,
)
from app.enrichment.llm_company import analyze_company_website
from app.enrichment.company_details import enrich_company_details
from app.enrichment.icp_validator import validate_lead_against_icp
from app.sync.zims import push_lead_to_zims


SOCIAL_DOMAINS: frozenset[str] = frozenset({
    "facebook.com",
    "fb.com",
    "linkedin.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "pinterest.com",
    "wa.me",
    "wa.link",
    "whatsapp.com",
    "t.me",
    "telegram.me",
    "threads.net",
    "snapchat.com",
    "lnkd.in",
    "bit.ly",
    "linktr.ee",
    "beacons.ai",
    "linkinbio.com",
})

# Maps social base domain → company field name
_SOCIAL_FIELD: dict[str, str] = {
    "facebook.com": "facebook_url",
    "fb.com": "facebook_url",
    "linkedin.com": "linkedin_url",
    "lnkd.in": "linkedin_url",
    "instagram.com": "instagram_url",
    "twitter.com": "twitter_url",
    "x.com": "twitter_url",
    "tiktok.com": "tiktok_url",
    "youtube.com": "youtube_url",
    "threads.net": "instagram_url",
}

# Words that should never appear as the FIRST word of a real person's name.
# Uses whole-word matching to avoid false positives like "Homer" blocking on "home".
_NAME_FIRST_WORD_BLOCKLIST: frozenset[str] = frozenset({
    # Marketing / navigation copy
    "introducing", "read", "catch", "see", "click", "follow", "learn",
    "sign", "log", "contact", "about", "get", "find", "discover",
    "welcome", "thank", "hello", "hi", "hey",
    # Insurance product names that look like names
    "home", "life", "medical", "motor", "auto", "travel", "health",
    "fire", "marine", "cargo", "takaful", "protect", "safe", "secure",
    "my", "your", "our", "the",
    # Meta / social noise
    "meta", "and", "but", "or", "for", "in", "at",
})
_NAME_ANY_WORD_BLOCKLIST: frozenset[str] = frozenset({
    "about",
    "advisory",
    "advisor",
    "announcements",
    "app",
    "campaigns",
    "charter",
    "claims",
    "component",
    "consent",
    "contact",
    "cookie",
    "cookies",
    "doctor",
    "events",
    "faq",
    "financial",
    "find",
    "football",
    "foreign",
    "form",
    "glossary",
    "guide",
    "help",
    "human",
    "important",
    "insurance",
    "investment",
    "library",
    "locate",
    "office",
    "overview",
    "partnerships",
    "payment",
    "personnel",
    "preference",
    "preferences",
    "premium",
    "privacy",
    "promotions",
    "public",
    "read",
    "recordkeeping",
    "registration",
    "renew",
    "resource",
    "resources",
    "running",
    "specialist",
    "success",
    "support",
    "technical",
    "terms",
    "wellness",
})
_NAME_CONNECTORS: frozenset[str] = frozenset({
    "al", "ap", "bin", "binti", "da", "de", "del", "der", "di", "ibn",
    "la", "le", "md", "mohd", "van", "von",
})
_TITLE_TOKEN_BLOCKLIST: frozenset[str] = frozenset({
    "about",
    "announcements",
    "app",
    "campaigns",
    "charter",
    "claims",
    "contact",
    "events",
    "faq",
    "find",
    "football",
    "form",
    "glossary",
    "guide",
    "help",
    "important",
    "investment",
    "library",
    "locate",
    "overview",
    "partnerships",
    "payment",
    "premium",
    "promotions",
    "public",
    "read",
    "registration",
    "running",
    "specialist",
    "support",
    "terms",
    "wellness",
})


def _normalize_person_text(value: str) -> str:
    text = (value or "").replace("\u200b", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_domain(url: str | None) -> str | None:
    """
    Parse registrable-style host from URL.

    ``https://company.com/page`` → ``company.com``
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


def _base_domain(url: str | None) -> str | None:
    """
    Return the registrable base domain (last two labels) of a URL.

    ``https://m.facebook.com/page`` → ``facebook.com``
    """
    host = extract_domain(url)
    if not host:
        return None
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _social_field_for_url(url: str | None) -> str | None:
    """
    Return the ZLCompany field name if ``url`` belongs to a social platform.

    Returns None for ordinary company websites.
    """
    base = _base_domain(url)
    if not base:
        return None
    return _SOCIAL_FIELD.get(base) or ("facebook_url" if base in SOCIAL_DOMAINS else None)


def _is_valid_person_name(name: str) -> bool:
    """
    Return True only when ``name`` looks like a real human name.

    Rejects long sentences, product names, marketing copy, and strings
    scraped from social media or navigation elements.
    """
    if not name:
        return False
    stripped = _normalize_person_text(name)
    # Hard length ceiling — real names fit in 60 chars
    if len(stripped) > 60:
        return False
    words = stripped.split()
    # Must have at least 2 words (first + last) and at most 5
    if len(words) < 2 or len(words) > 5:
        return False
    # Reject if the first word is a known non-name token (whole-word match)
    if words[0].lower() in _NAME_FIRST_WORD_BLOCKLIST:
        return False
    # Reject strings that contain digits (phone numbers, "3 min read", etc.)
    if any(ch.isdigit() for ch in stripped):
        return False
    if any(ch in stripped for ch in "@/|\\"):
        return False
    human_tokens = 0
    for raw_word in words:
        word = raw_word.strip(".,:;()[]{}\"'")
        lower = word.lower()
        if not word:
            return False
        if lower in _NAME_ANY_WORD_BLOCKLIST:
            return False
        if lower in _NAME_CONNECTORS:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\\-]{0,24}", word):
            return False
        if not word[0].isupper():
            return False
        human_tokens += 1
    return human_tokens >= 2


def _sanitize_person_title(title: str | None) -> str:
    """
    Return a conservative contact title.

    Marketing copy and navigation labels should never contribute role points.
    """
    cleaned = _normalize_person_text(title or "")
    if not cleaned:
        return "Unknown"
    words = cleaned.split()
    if len(cleaned) > 100 or len(words) > 12:
        return "Unknown"
    if any(ch.isdigit() for ch in cleaned):
        return "Unknown"
    lowered = cleaned.lower()
    if "http://" in lowered or "https://" in lowered or ".com" in lowered:
        return "Unknown"
    if any(word.strip(".,:;()[]{}\"'").lower() in _TITLE_TOKEN_BLOCKLIST for word in words):
        return "Unknown"
    return cleaned


def _email_matches_person_name(email: str | None, first_name: str, last_name: str) -> bool:
    """
    Return True when an email local-part plausibly belongs to the named person.

    This prevents generic website emails or another employee's mailbox from being
    attached to the wrong contact.
    """
    if not email or "@" not in email:
        return False

    first = re.sub(r"[^a-z0-9]", "", (first_name or "").lower())
    last = re.sub(r"[^a-z0-9]", "", (last_name or "").lower())
    if not first or not last:
        return False

    local_part = re.sub(r"[^a-z0-9]", "", email.split("@", 1)[0].lower())
    if not local_part:
        return False

    patterns = {
        first,
        last,
        f"{first}{last}",
        f"{first[0]}{last}",
        f"{first}.{last}".replace(".", ""),
        f"{first}{last[0]}",
    }
    return any(pattern and pattern in local_part for pattern in patterns)


def _looks_like_generic_contact_label(name: str, title: str | None) -> bool:
    """
    Reject department names, navigation labels, and generic role strings.
    """
    cleaned_name = _normalize_person_text(name)
    if not cleaned_name:
        return True
    lowered = cleaned_name.lower()
    if lowered == _normalize_person_text(title or "").lower():
        return True
    if cleaned_name.isupper():
        return True
    generic_phrases = (
        "chief executive officer",
        "manage consent preferences",
        "privacy preference center",
        "strictly necessary cookies",
        "renew your insurance",
        "head office",
        "human capital",
        "financial wellbeing",
        "technical advisor",
        "advisory personnel",
    )
    if any(phrase in lowered for phrase in generic_phrases):
        return True
    return False


# ── Company name keyword → intent signal mapping ─────────────────
# These add signal score points when the ICP includes matching intent_signals.
_NAME_SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "expanding": [
        "tech", "technology", "solutions", "group", "global", "enterprise",
        "holdings", "corporation", "systems", "digital", "innovation",
        "consulting", "services", "integrated", "network", "partner",
    ],
    "hiring": [
        "software", "it ", " i.t", "developer", "engineering", "data",
        "cyber", "cloud", "ai ", "artificial intelligence", "machine learning",
    ],
}


def _detect_signals_from_company_name(company_name: str) -> list[str]:
    """
    Detect intent signals from company name keywords.
    E.g. 'Tech', 'Solutions', 'Group' → expanding
         'Software', 'IT', 'Developer' → hiring
    """
    if not company_name:
        return []
    lowered = company_name.lower()
    detected: list[str] = []
    for signal, keywords in _NAME_SIGNAL_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            if signal not in detected:
                detected.append(signal)
    return detected


def _extract_name_from_company_name(company_name: str) -> str | None:
    """
    Extract a person name from a company name string.

    Malaysian insurance agents on Google Maps often list their business as
    "AIA Medical Card - Jason Khor" or "ING Life Insurance (Ahmad Razif)".
    We detect these patterns and return the candidate name.
    """
    if not company_name:
        return None

    # Pattern 1: "Company Name - Person Name" (last segment after dash)
    parts = company_name.rsplit(" - ", 1)
    if len(parts) == 2:
        candidate = parts[1].strip()
        # Must look like a name: 2–4 words, no slashes, no digits
        if (
            2 <= len(candidate.split()) <= 4
            and "/" not in candidate
            and not any(ch.isdigit() for ch in candidate)
            and _is_valid_person_name(candidate)
        ):
            return candidate

    # Pattern 2: "(Person Name)" at the end  e.g. "Great Eastern (Lim Wei Chen)"
    match = re.search(r"\(([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)+)\)\s*$", company_name)
    if match:
        candidate = match.group(1)
        if _is_valid_person_name(candidate):
            return candidate

    return None


async def check_suppression(
    email: str | None,
    domain: str | None,
    user_id: str,
    db: AsyncSession,
) -> bool:
    """
    Return True if email or domain appears on suppression list for this user
    or globally (``user_id`` NULL).
    """
    from sqlalchemy import and_, or_

    clauses: list[Any] = []
    if email:
        em = email.lower().strip()
        clauses.append(
            and_(ZLSuppressionList.value_type == "email", ZLSuppressionList.value == em)
        )
    if domain:
        dom = domain.lower().strip().lstrip("@")
        clauses.append(
            and_(ZLSuppressionList.value_type == "domain", ZLSuppressionList.value == dom)
        )
    if not clauses:
        return False

    stmt = (
        select(ZLSuppressionList)
        .where(
            or_(*clauses),
            or_(ZLSuppressionList.user_id == user_id, ZLSuppressionList.user_id.is_(None)),
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def upsert_company(data: dict[str, Any], db: AsyncSession) -> ZLCompany:
    """
    Insert or update a company row.

    Match priority: ``google_maps_id`` first, then ``domain``.

    Google Maps sometimes returns a social media URL (e.g. a Facebook page) as the
    place's ``website`` field.  We detect these and store them in the correct social
    link column so the website scraper never tries to crawl them.
    """
    gid = data.get("google_maps_id")
    website = data.get("website")

    # Reclassify social URLs: store in the appropriate social field, never as website/domain.
    social_field = _social_field_for_url(website)
    if social_field:
        if not data.get(social_field):
            data[social_field] = website
        logger.debug(f"Reclassified social URL {website!r} → {social_field}")
        website = None
        data["website"] = None

    domain = extract_domain(website) if website else None

    existing: ZLCompany | None = None
    if gid:
        res = await db.execute(select(ZLCompany).where(ZLCompany.google_maps_id == gid))
        existing = res.scalar_one_or_none()
    if existing is None and domain:
        res = await db.execute(select(ZLCompany).where(ZLCompany.domain == domain))
        existing = res.scalar_one_or_none()

    if existing:
        existing.name = data.get("name") or existing.name
        if website:
            existing.website = website
        if domain:
            existing.domain = domain
        if data.get("industry") and existing.industry is None:
            existing.industry = data.get("industry")
        if data.get("phone"):
            existing.phone = data.get("phone")
        if data.get("address"):
            existing.address = data.get("address")
        if data.get("city"):
            existing.city = data.get("city")
        if data.get("country"):
            existing.country = data.get("country")
        if data.get("google_rating") is not None:
            existing.google_rating = data.get("google_rating")
        if data.get("google_reviews") is not None:
            existing.google_reviews = data.get("google_reviews")
        if data.get("latitude") is not None:
            existing.latitude = data.get("latitude")
        if data.get("longitude") is not None:
            existing.longitude = data.get("longitude")
        if data.get("facebook_url") and existing.facebook_url is None:
            existing.facebook_url = data.get("facebook_url")
        if data.get("linkedin_url") and existing.linkedin_url is None:
            existing.linkedin_url = data.get("linkedin_url")
        if data.get("instagram_url") and existing.instagram_url is None:
            existing.instagram_url = data.get("instagram_url")
        existing.data_source = LeadSource.GOOGLE_MAPS
        await db.flush()
        return existing

    company = ZLCompany(
        name=data.get("name") or "Unknown",
        domain=domain,
        website=website,
        industry=data.get("industry"),
        phone=data.get("phone"),
        address=data.get("address"),
        city=data.get("city"),
        country=data.get("country"),
        google_maps_id=gid,
        google_rating=data.get("google_rating"),
        google_reviews=data.get("google_reviews"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        facebook_url=data.get("facebook_url"),
        linkedin_url=data.get("linkedin_url"),
        instagram_url=data.get("instagram_url"),
        data_source=LeadSource.GOOGLE_MAPS,
    )
    db.add(company)
    await db.flush()
    return company


async def upsert_person(data: dict[str, Any], db: AsyncSession) -> ZLPerson:
    """
    Insert or update a person for a company.

    Match on ``full_name`` + ``company_id``. Upgrades email when confidence improves.
    """
    company_id = data["company_id"]
    full_name = data.get("full_name") or data.get("name") or "Unknown"
    res = await db.execute(
        select(ZLPerson).where(ZLPerson.company_id == company_id, ZLPerson.full_name == full_name)
    )
    existing = res.scalar_one_or_none()

    new_email = data.get("email")
    new_conf = float(data.get("email_confidence") or 0.0)
    new_verified = bool(data.get("email_verified", False))

    if existing:
        _existing_conf = float(existing.email_confidence or 0.0)
        better = (new_email and new_conf > _existing_conf) or (
            new_email and new_conf == _existing_conf and new_verified
        )
        if better:
            existing.email = new_email
            existing.email_verified = new_verified
            existing.email_confidence = new_conf
            existing.email_source = data.get("email_source") or existing.email_source
        if data.get("job_title"):
            existing.job_title = data.get("job_title")
        if data.get("phone"):
            existing.phone = data.get("phone")
        if data.get("linkedin_url"):
            existing.linkedin_url = data.get("linkedin_url")
        if data.get("first_name"):
            existing.first_name = data.get("first_name")
        if data.get("last_name"):
            existing.last_name = data.get("last_name")
        if data.get("seniority"):
            existing.seniority = data.get("seniority")
        existing.data_source = data.get("data_source") or existing.data_source or LeadSource.WEBSITE
        await db.flush()
        return existing

    person = ZLPerson(
        company_id=company_id,
        full_name=full_name,
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        job_title=data.get("job_title"),
        seniority=data.get("seniority"),
        email=new_email,
        email_verified=new_verified,
        email_confidence=new_conf,
        email_source=data.get("email_source"),
        phone=data.get("phone"),
        linkedin_url=data.get("linkedin_url"),
        data_source=data.get("data_source") or LeadSource.WEBSITE,
    )
    db.add(person)
    await db.flush()
    return person


async def generate_leads_for_icp(user_id: str, icp_id: str, db: AsyncSession) -> dict[str, int]:
    """
    Full lead generation pipeline for one ICP.

    Scrapes companies, enriches via website, verifies email, scores, persists hot+
    leads, and schedules ZIMS push for HOT leads.
    """
    icp = await db.get(ZLICP, icp_id)
    if icp is None or str(icp.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ICP not found.")

    user = await db.get(ZLUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if int(user.leads_used_this_month or 0) >= int(user.leads_limit or 0):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Monthly lead limit reached",
                "used": user.leads_used_this_month,
                "limit": user.leads_limit,
                "upgrade_url": "/dashboard/billing",
            },
        )

    counters: dict[str, int] = {
        "generated": 0,
        "skipped_existing": 0,
        "skipped_cold": 0,
        "skipped_suppressed": 0,
        "errors": 0,
        "hot": 0,
        "warm": 0,
        "potential": 0,
    }
    committed_generated = 0

    queries_raw: list[str] = [str(q) for q in (icp.search_queries or [])]
    industries: list[str] = [str(i) for i in (icp.industries or [])]
    locations: list[str] = [str(l) for l in (icp.locations or [])]

    if queries_raw:
        # search_queries are self-contained Maps queries that already embed the city
        # (e.g. "insurance broker Kuala Lumpur"). Do NOT append a separate location
        # or the scraper produces "insurance broker Penang Kuala Lumpur" — wrong city
        # and a different cache key than expected.
        queries = queries_raw[:8]
        location = ""
        logger.info(f"ICP {icp_id}: using {len(queries)} search_queries (city embedded), location=''")
    elif industries and locations:
        queries = [f"{industries[0]} {locations[0]}"]
        location = ""
        logger.info(f"ICP {icp_id}: no search_queries — derived from industries+locations: {queries}")
    else:
        queries = [str(icp.name or "")]
        location = locations[0] if locations else ""
        logger.warning(
            f"ICP {icp_id} ('{icp.name}') has no search_queries, industries, or locations. "
            f"Falling back to ICP name as search query. "
            f"Use POST /api/v1/icp/build to generate a properly populated ICP."
        )

    logger.info(f"ICP {icp_id}: running {len(queries)} queries — {queries}")

    for query in queries:
        try:
            companies = await scrape_google_maps(str(query), str(location), max_results=20)
        except Exception as exc:
            logger.error(f"Maps scrape failed: {exc}")
            counters["errors"] += 1
            continue

        # Fetch RSS funding articles ONCE for all companies in this batch
        rss_articles = await scan_all_rss_feeds()
        logger.info(f"Pre-fetched {len(rss_articles)} RSS funding articles for batch")

        for company_data in companies:
            try:
                company = await upsert_company(company_data, db)

                site_data: dict[str, Any] = {}
                company_website: str | None = str(company.website) if company.website is not None else None
                if company_website:
                    site_data = await scrape_company_website(company_website)

                # ── LLM Company Enrichment ─────────────────────────
                # Use Claude to extract employee count, industry, signals from website text
                website_text = str(site_data.get("raw_text") or "")
                llm_enrichment = await analyze_company_website(
                    raw_text=website_text,
                    company_name=str(company.name or ""),
                    maps_category=str(company.industry or ""),
                )
                if llm_enrichment.get("confidence", 0) > 0.3:
                    if llm_enrichment.get("employee_range") and not company.employee_range:
                        company.employee_range = llm_enrichment["employee_range"]
                    if llm_enrichment.get("industry"):
                        company.industry = llm_enrichment["industry"]
                    if llm_enrichment.get("sub_industry"):
                        company.sub_industry = llm_enrichment["sub_industry"]
                await db.flush()

                # Write social links back from the website scraper
                social = site_data.get("social") or {}
                if social.get("linkedin") and company.linkedin_url is None:
                    company.linkedin_url = social["linkedin"]
                if social.get("facebook") and company.facebook_url is None:
                    company.facebook_url = social["facebook"]
                if social.get("instagram") and company.instagram_url is None:
                    company.instagram_url = social["instagram"]
                await db.flush()

                # ── Company Detail Enrichment ──────────────────────
                # SSM, revenue, years, LinkedIn, decision maker
                company_domain: str | None = str(company.domain) if company.domain is not None else None
                domain: str | None = company_domain or extract_domain(company_website)
                people = site_data.get("people") or []

                details = enrich_company_details(
                    company_name=str(company.name or ""),
                    domain=domain,
                    industry=str(company.industry or ""),
                    employee_range=str(company.employee_range or ""),
                    founded_year=company.founded_year,
                    website_raw_text=website_text,
                    people=people,
                )
                if details.get("ssm_verified") is not None:
                    company.ssm_verified = details["ssm_verified"]
                if details.get("revenue"):
                    company.revenue = details["revenue"]
                if details.get("years_in_business"):
                    company.years_in_business = details["years_in_business"]
                if details.get("linkedin_url") and not company.linkedin_url:
                    company.linkedin_url = details["linkedin_url"]
                await db.flush()

                # Update best decision maker name if found
                if details.get("decision_maker_name") and people:
                    # Find the matching person and update their name
                    for p in people:
                        if p.get("name") == details.get("decision_maker_name"):
                            p["_best_dm"] = True
                            break

                # Fallback for companies with no scrapeable website (social URLs,
                # wa.link, etc.) — very common for Malaysian insurance agents who
                # list their personal name inside the Google Maps business name,
                # e.g. "AIA Medical Card - Jason Khor".
                if not people:
                    extracted = _extract_name_from_company_name(str(company.name or ""))
                    if extracted:
                        logger.info(
                            f"Extracted agent name {extracted!r} from company name "
                            f"{company.name!r}"
                        )
                        people = [{"name": extracted, "title": "Insurance Agent"}]
                    else:
                        # No scrapeable people — create synthetic placeholder so
                        # company-level enrichment still produces a scored lead.
                        people = [{"name": "Decision Maker", "title": "Director", "_synthetic": True}]

                for person_data in people[:5]:
                    try:
                        raw_name = _normalize_person_text(person_data.get("name") or "")
                        if not _is_valid_person_name(raw_name):
                            logger.debug(f"Rejected invalid person name: {raw_name!r}")
                            continue
                        name_parts = raw_name.split(" ", 1)
                        first = name_parts[0] if name_parts else ""
                        last = name_parts[1] if len(name_parts) > 1 else ""
                        title_guess = _sanitize_person_title(person_data.get("title"))
                        if _looks_like_generic_contact_label(raw_name, title_guess):
                            logger.debug(f"Rejected generic contact label: {raw_name!r}")
                            continue

                        email_result: dict[str, Any] = {
                            "email": None,
                            "valid": False,
                            "confidence": 0.0,
                            "method": "none",
                        }
                        is_synthetic = person_data.get("_synthetic", False)
                        if first and last and domain and title_guess != "Unknown" and not is_synthetic:
                            email_result = await find_best_email(first, last, str(domain))
                        elif is_synthetic and domain:
                            # Try role-based email patterns for synthetic contacts
                            role = re.sub(r"[^a-z0-9]", "", (title_guess or "director").lower()) or "director"
                            email_result = await find_role_email(str(domain), role=role)
                        elif site_data.get("emails"):
                            website_email = site_data["emails"][0]
                            if not _email_matches_person_name(website_email, first, last):
                                website_email = None
                            if website_email:
                                email_result = {
                                    "email": website_email,
                                    "valid": True,
                                    "confidence": 0.7,
                                    "method": "website",
                                }
                        cand_email_raw = email_result.get("email")
                        if cand_email_raw and not is_synthetic and not _email_matches_person_name(
                            str(cand_email_raw),
                            first,
                            last,
                        ):
                            email_result = {
                                "email": None,
                                "valid": False,
                                "confidence": 0.0,
                                "method": "none",
                            }
                            cand_email_raw = None
                        if cand_email_raw and str(cand_email_raw).strip():
                            em_lower = str(cand_email_raw).strip().lower()
                            dup_by_email = await db.execute(
                                select(ZLLead.id)
                                .join(ZLPerson, ZLLead.person_id == ZLPerson.id)
                                .where(
                                    ZLLead.user_id == user_id,
                                    func.lower(ZLPerson.email) == em_lower,
                                )
                                .limit(1)
                            )
                            if dup_by_email.scalar_one_or_none():
                                logger.debug(
                                    f"Skip person: user already has a lead with email {em_lower!r}"
                                )
                                counters["skipped_existing"] += 1
                                continue

                        seniority = _infer_seniority_from_title(title_guess)

                        # Prefer website-scraped phone, fallback to Google Maps phone
                        contact_phone = (
                            (site_data.get("phones") or [None])[0]
                            or company.phone
                        )

                        person = await upsert_person(
                            {
                                "name": raw_name,
                                "full_name": raw_name,
                                "first_name": first,
                                "last_name": last,
                                "job_title": title_guess,
                                "seniority": seniority,
                                "company_id": company.id,
                                "email": email_result.get("email"),
                                "email_verified": bool(email_result.get("valid", False)),
                                "email_confidence": float(email_result.get("confidence", 0.0)),
                                "email_source": str(email_result.get("method") or "unknown"),
                                "phone": contact_phone,
                                "linkedin_url": (site_data.get("social") or {}).get("linkedin"),
                                "data_source": LeadSource.WEBSITE,
                            },
                            db,
                        )

                        # ── Intent enrichment ──────────────────────────────
                        website_text = str(site_data.get("raw_text") or "")
                        intent_result = await enrich_company_intent(
                            company_name=str(company.name or ""),
                            website_text=website_text,
                            existing_signals=[
                                s for s in [
                                    "hiring" if company.is_hiring else None,
                                    "funded" if company.funding_stage else None,
                                    "in_the_news" if company.in_the_news else None,
                                ] if s is not None
                            ],
                            rss_articles=rss_articles,
                        )
                        enriched_signals = intent_result["signals"]
                        why_now = intent_result["why_now"]
                        competitor_tool = intent_result["primary_competitor"]

                        # Update company with new intent data
                        company.is_hiring = company.is_hiring or intent_result["job_count"] > 0
                        if intent_result["job_count"] > 0:
                            company.job_posting_count = intent_result["job_count"]

                        person_dict = {
                            "job_title": str(person.job_title or ""),
                            "seniority": str(person.seniority or ""),
                            "email": str(person.email) if person.email is not None else None,
                            "email_verified": bool(person.email_verified),
                            "email_confidence": float(person.email_confidence or 0.0),
                            "job_changed_at": person.job_changed_at,
                            "first_name": str(person.first_name or ""),
                            "full_name": str(person.full_name or ""),
                        }
                        # Merge LLM-enriched signals with intent signals
                        enriched_signals = list(intent_result["signals"])
                        for sig in (llm_enrichment.get("signals_detected") or []):
                            if sig not in enriched_signals:
                                enriched_signals.append(sig)

                        # Detect signals from company name keywords
                        name_signals = _detect_signals_from_company_name(str(company.name or ""))

                        # Merge all detected signals (intent + LLM + name-based)
                        all_detected_signals = list(enriched_signals)
                        for sig in name_signals:
                            if sig not in all_detected_signals:
                                all_detected_signals.append(sig)

                        company_dict = {
                            "industry": str(company.industry or ""),
                            "employee_range": str(company.employee_range or ""),
                            "is_hiring": bool(company.is_hiring) or "hiring" in all_detected_signals,
                            "in_the_news": bool(company.in_the_news) or "in_the_news" in all_detected_signals,
                            "funding_stage": str(company.funding_stage or ""),
                            "name": str(company.name or ""),
                            "city": str(company.city or ""),
                            "country": str(company.country or ""),
                        }
                        icp_dict = {
                            "industries": list(icp.industries or []),
                            "job_titles": list(icp.job_titles or []),
                            "seniority_levels": list(icp.seniority_levels or []),
                            "company_sizes": list(icp.company_sizes or []),
                            "intent_signals": list(icp.intent_signals or []),
                        }

                        # Score using original ICP intent_signals as the match target,
                        # with all detected signals passed as extra_signals.
                        score_result = calculate_lead_score(
                            person_dict,
                            company_dict,
                            icp_dict,
                            extra_signals=all_detected_signals,
                            icp_match_score=icp_validation.get("match_score"),
                        )

                        # Store cold leads — they're real contacts and visible in the UI.
                        # Only skip the absolute floor: real person but literally zero score
                        # and no email (nothing to work with at all).
                        _person_email: str | None = str(person.email) if person.email is not None else None
                        _company_domain: str | None = str(company.domain) if company.domain is not None else None

                        if score_result["score"] == 0 and not _person_email:
                            counters["skipped_cold"] += 1
                            continue

                        if _person_email:
                            sup = await check_suppression(
                                _person_email,
                                _company_domain,
                                user_id,
                                db,
                            )
                            if sup:
                                counters["skipped_suppressed"] += 1
                                continue

                        existing = await db.execute(
                            select(ZLLead).where(
                                ZLLead.user_id == user_id,
                                ZLLead.person_id == person.id,
                            ).limit(1)
                        )
                        if existing.scalar_one_or_none():
                            counters["skipped_existing"] += 1
                            continue

                        outreach: dict[str, str] = {}
                        if score_result["score"] >= 60:
                            signals = score_result["breakdown"].get("signals_detected", [])
                            outreach = await generate_ai_outreach(
                                person_dict,
                                company_dict,
                                str(icp.description or icp.name or ""),
                                signals,
                                why_now=why_now,
                                competitor_tool=competitor_tool,
                            )

                        # ── ICP Validation ─────────────────────────────────
                        icp_validation = await validate_lead_against_icp(
                            company_name=str(company.name or ""),
                            company_industry=str(company.industry or ""),
                            company_description=None,
                            company_size=str(company.employee_range or ""),
                            company_city=str(company.city or ""),
                            icp_description=str(icp.description or icp.name or ""),
                            icp_industries=list(icp.industries or []),
                        )

                        lead = ZLLead(
                            user_id=user_id,
                            icp_id=icp_id,
                            person_id=person.id,
                            company_id=company.id,
                            lead_score=score_result["score"],
                            lead_tier=LeadTier[score_result["tier"].upper()],
                            score_breakdown=score_result["breakdown"],
                            intent_signals=enriched_signals,
                            source=LeadSource.GOOGLE_MAPS,
                            ai_whatsapp_msg=outreach.get("whatsapp_message"),
                            ai_email_subject=outreach.get("email_subject"),
                            ai_email_body=outreach.get("email_body"),
                            ai_linkedin_note=outreach.get("linkedin_note"),
                            icp_match_score=icp_validation.get("match_score"),
                            icp_verdict=icp_validation.get("verdict"),
                            icp_reason=icp_validation.get("reason"),
                            recommended_product=icp_validation.get("recommended_product"),
                        )
                        db.add(lead)
                        await db.flush()

                        # Track conversion event: lead_generated
                        await track_lead_generated(db, lead)

                        counters["generated"] += 1
                        tier_key = score_result["tier"]
                        if tier_key in counters:
                            counters[tier_key] += 1

                        if score_result["score"] >= 85:
                            asyncio.create_task(push_lead_to_zims(str(lead.id)))

                    except Exception as exc:
                        logger.error(f"Person processing error: {exc}")
                        counters["errors"] += 1
                        continue

            except Exception as exc:
                logger.error(f"Company processing error: {exc}")
                counters["errors"] += 1
                continue

            delta_generated = counters["generated"] - committed_generated
            if delta_generated > 0:
                # Atomic increment with limit guard — prevents race-condition overshoot
                result = await db.execute(
                    update(ZLUser)
                    .where(
                        ZLUser.id == user_id,
                        func.coalesce(ZLUser.leads_used_this_month, 0) + delta_generated
                        <= func.coalesce(ZLUser.leads_limit, 0),
                    )
                    .values(
                        leads_used_this_month=func.coalesce(ZLUser.leads_used_this_month, 0)
                        + delta_generated,
                    )
                )
                if result.rowcount == 0:
                    logger.warning(f"User {user_id} hit lead limit mid-generation. Stopping.")
                    break

                await db.execute(
                    update(ZLICP)
                    .where(ZLICP.id == icp_id)
                    .values(
                        total_leads_generated=func.coalesce(ZLICP.total_leads_generated, 0)
                        + delta_generated,
                    )
                )
                committed_generated = counters["generated"]

            # Commit after each company so leads appear in the UI progressively
            # rather than only after the entire job finishes.
            await db.commit()

    return counters


async def run_lead_generation_job(user_id: str, icp_id: str) -> None:
    """
    Background-safe entrypoint that owns its own DB session.

    Commits after each company so results appear progressively in the UI
    rather than only after the entire job finishes.
    """
    async with AsyncSessionLocal() as db:
        try:
            summary = await generate_leads_for_icp(user_id, icp_id, db)
            await db.commit()
            logger.info(f"Lead generation job finished for icp={icp_id}: {summary}")
        except HTTPException:
            await db.rollback()
            logger.warning(f"Lead generation job aborted for icp={icp_id} (HTTP error)")
        except Exception:
            await db.rollback()
            logger.exception(f"Lead generation job failed for icp={icp_id}")
