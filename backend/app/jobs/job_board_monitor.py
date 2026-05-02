"""
Job Board Monitor — Detect insurance buying signals from hiring posts.

Scrapes Indeed RSS feeds for Malaysian job postings,
maps job titles to insurance products, then upgrades
existing leads or flags companies for follow-up.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import (
    LeadSource,
    LeadStatus,
    LeadTier,
    ZLAutoSignal,
    ZLCompany,
    ZLICP,
    ZLLead,
    ZLLeadHistory,
    ZLPerson,
    ZLUser,
)

# ═══════════════════════════════════════════════════════════════
# Job Title → Insurance Signal Mapping
# ═══════════════════════════════════════════════════════════════

JOB_SIGNALS: dict[str, dict[str, Any]] = {
    "lorry driver": {
        "product": "Fleet/Commercial Vehicle Insurance",
        "signal": "hiring_drivers",
        "score_boost": 15,
        "why_now": "Hiring lorry drivers — fleet insurance expansion likely needed",
    },
    "pemandu lori": {
        "product": "Fleet/Commercial Vehicle Insurance",
        "signal": "hiring_drivers",
        "score_boost": 15,
        "why_now": "Hiring lorry drivers — fleet insurance expansion likely needed",
    },
    "site supervisor": {
        "product": "Workmanship Liability Insurance",
        "signal": "construction_hiring",
        "score_boost": 15,
        "why_now": "Hiring site supervisors — workmanship liability review needed",
    },
    "safety officer": {
        "product": "Workmanship Liability + SOCSO",
        "signal": "safety_expansion",
        "score_boost": 15,
        "why_now": "Hiring safety officer — liability coverage review needed",
    },
    "warehouse supervisor": {
        "product": "Fire + Cargo Insurance",
        "signal": "warehouse_expansion",
        "score_boost": 12,
        "why_now": "Warehouse hiring — fire and cargo coverage may need updating",
    },
    "factory operator": {
        "product": "Workers Compensation + Fire",
        "signal": "manufacturing_hiring",
        "score_boost": 10,
        "why_now": "Factory expansion — workers compensation update needed",
    },
    "delivery rider": {
        "product": "Motor Insurance",
        "signal": "fleet_expansion",
        "score_boost": 10,
        "why_now": "Hiring delivery riders — motor insurance expansion needed",
    },
    "hr executive": {
        "product": "Group Medical Card",
        "signal": "hr_setup",
        "score_boost": 10,
        "why_now": "Setting up HR function — ideal time for group medical card",
    },
    "general worker": {
        "product": "Workers Compensation",
        "signal": "workforce_expansion",
        "score_boost": 8,
        "why_now": "Growing workforce — workers compensation review needed",
    },
    "crane operator": {
        "product": "Equipment + Workmanship Insurance",
        "signal": "heavy_equipment",
        "score_boost": 15,
        "why_now": "Heavy equipment operator — equipment insurance review needed",
    },
}

# ═══════════════════════════════════════════════════════════════
# Indeed RSS Feeds
# ═══════════════════════════════════════════════════════════════

def _indeed_rss_url(job_title: str) -> str:
    """Build Indeed RSS URL for a job search in Malaysia."""
    q = job_title.replace(" ", "+")
    return f"https://malaysia.indeed.com/rss?q={q}&l=Malaysia"


INDEED_RSS_FEEDS: dict[str, str] = {
    job: _indeed_rss_url(job)
    for job in JOB_SIGNALS.keys()
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml,application/xml,text/xml,*/*",
}


# ═══════════════════════════════════════════════════════════════
# RSS Parsing
# ═══════════════════════════════════════════════════════════════


def _clean_company_name(raw: str, job_title: str) -> str:
    """
    Clean company name extracted from job postings.
    Removes location suffixes, job titles, and common noise.
    """
    if not raw:
        return ""

    cleaned = raw.strip()

    # Remove location patterns
    patterns = [
        r"\s*[-–—]\s*Kuala Lumpur.*$",
        r"\s*[-–—]\s*Selangor.*$",
        r"\s*[-–—]\s*Penang.*$",
        r"\s*[-–—]\s*Johor.*$",
        r"\s*[-–—]\s*Malaysia.*$",
        r"\s*\([^)]*\)\s*$",
        r"\s*\[[^\]]*\]\s*$",
    ]
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.I)

    # Remove job title if accidentally included
    cleaned = re.sub(re.escape(job_title), "", cleaned, flags=re.I)

    cleaned = cleaned.strip("-–—| ")
    return cleaned


def _extract_company_from_job_title(title: str, job_title: str) -> str | None:
    """
    Extract company name from an Indeed job title.
    Indeed titles are often: "Job Title at Company Name" or "Job Title - Company Name"
    """
    if not title:
        return None

    # Pattern 1: "... at Company Name"
    match = re.search(r"\bat\s+([^\-–—|]+)$", title, re.I)
    if match:
        return _clean_company_name(match.group(1), job_title)

    # Pattern 2: "... - Company Name"
    parts = re.split(r"[-–—|]", title, maxsplit=1)
    if len(parts) == 2:
        return _clean_company_name(parts[1], job_title)

    # Pattern 3: first few words before job title keywords
    lowered = title.lower()
    for kw in [job_title.lower(), "urgent", "new"]:
        if kw in lowered:
            before = title.split(kw, 1)[0].strip()
            if len(before) >= 3:
                return _clean_company_name(before, job_title)

    return None


async def fetch_indeed_rss(job_title: str, url: str) -> list[dict[str, Any]]:
    """Fetch and parse Indeed RSS for a specific job title."""
    jobs: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as exc:
        logger.warning(f"Indeed RSS for '{job_title}' failed: {exc}")
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning(f"Indeed RSS for '{job_title}' parse error: {exc}")
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    for item in channel.findall("item"):
        title_elem = item.find("title")
        desc_elem = item.find("description")
        link_elem = item.find("link")
        author_elem = item.find("author") or item.find("{http://purl.org/dc/elements/1.1/}creator")
        date_elem = item.find("pubDate") or item.find("{http://purl.org/dc/elements/1.1/}date")

        title = (title_elem.text or "").strip() if title_elem is not None else ""
        description = (desc_elem.text or "").strip() if desc_elem is not None else ""
        link = (link_elem.text or "").strip() if link_elem is not None else ""
        author = (author_elem.text or "").strip() if author_elem is not None else ""
        pub_date = (date_elem.text or "").strip() if date_elem is not None else ""

        # Company name: prefer author, fallback to title extraction
        company_name = _clean_company_name(author, job_title) if author else None
        if not company_name or len(company_name) < 3:
            company_name = _extract_company_from_job_title(title, job_title)

        if not company_name or len(company_name) < 3:
            continue

        jobs.append({
            "job_title": job_title,
            "company_name": company_name,
            "title": title,
            "description": description,
            "url": link,
            "published_at": pub_date,
        })

    logger.info(f"Indeed RSS '{job_title}': {len(jobs)} jobs found")
    return jobs


# ═══════════════════════════════════════════════════════════════
# Google Custom Search Fallback
# ═══════════════════════════════════════════════════════════════


async def fetch_google_job_search(job_title: str) -> list[dict[str, Any]]:
    """
    Fallback: Use Google Custom Search API to find job postings.
    Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX in settings.
    """
    if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_CX:
        return []

    query = f"site:jobstreet.com.my OR site:maukerja.my {job_title} Malaysia"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.GOOGLE_SEARCH_API_KEY,
        "cx": settings.GOOGLE_SEARCH_CX,
        "q": query,
        "num": 10,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning(f"Google job search for '{job_title}' failed: {exc}")
        return []

    jobs: list[dict[str, Any]] = []
    for item in data.get("items", []):
        snippet = item.get("snippet", "")
        title = item.get("title", "")
        # Extract company from title/snippet heuristically
        company_name = _extract_company_from_job_title(title, job_title)
        if not company_name:
            # Try to find "Company Name - job title" in snippet
            match = re.search(r"([^,\n]{3,60}?)(?:\s+is hiring|\s+-\s+" + re.escape(job_title) + r")", snippet, re.I)
            if match:
                company_name = match.group(1).strip()
        if company_name and len(company_name) >= 3:
            jobs.append({
                "job_title": job_title,
                "company_name": company_name,
                "title": title,
                "description": snippet,
                "url": item.get("link", ""),
                "published_at": None,
            })

    logger.info(f"Google job search '{job_title}': {len(jobs)} jobs found")
    return jobs


# ═══════════════════════════════════════════════════════════════
# Database Operations
# ═══════════════════════════════════════════════════════════════


async def _find_company_by_name(db, name: str) -> ZLCompany | None:
    """Fuzzy match company by name."""
    if not name or len(name) < 3:
        return None

    result = await db.execute(
        select(ZLCompany).where(func.lower(ZLCompany.name) == name.lower())
    )
    company = result.scalar_one_or_none()
    if company:
        return company

    like_pattern = f"%{name.lower()}%"
    result = await db.execute(
        select(ZLCompany).where(func.lower(ZLCompany.name).like(like_pattern)).limit(1)
    )
    return result.scalar_one_or_none()


async def _find_existing_lead(db, user_id: str, company_id: str) -> ZLLead | None:
    result = await db.execute(
        select(ZLLead)
        .where(ZLLead.user_id == user_id, ZLLead.company_id == company_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _create_auto_signal(
    db,
    user_id: str | None,
    company_id: str | None,
    lead_id: str | None,
    company_name: str,
    signal_source: str,
    signal_type: str,
    why_now: str,
    insurance_need: str,
    recommended_product: str,
    source_url: str | None = None,
) -> ZLAutoSignal:
    signal = ZLAutoSignal(
        user_id=user_id,
        company_id=company_id,
        lead_id=lead_id,
        company_name=company_name,
        signal_source=signal_source,
        signal_type=signal_type,
        why_now=why_now,
        insurance_need=insurance_need,
        recommended_product=recommended_product,
        source_url=source_url,
        confidence=0.75,
    )
    db.add(signal)
    await db.flush()
    return signal


async def _get_active_users_with_icps(db) -> list[tuple[ZLUser, list[ZLICP]]]:
    result = await db.execute(
        select(ZLUser)
        .where(ZLUser.is_active == True)
        .options(selectinload(ZLUser.icps))
    )
    users = result.scalars().unique().all()
    out: list[tuple[ZLUser, list[ZLICP]]] = []
    for user in users:
        active_icps = [icp for icp in user.icps if icp.is_active]
        if active_icps:
            out.append((user, active_icps))
    return out


# ═══════════════════════════════════════════════════════════════
# Main Job
# ═══════════════════════════════════════════════════════════════


async def run_job_board_monitor() -> dict[str, Any]:
    """
    Main job board monitor job.
    Scrapes Indeed RSS (and Google fallback), maps jobs to insurance signals,
    upgrades existing leads, and creates auto-signal records.
    """
    logger.info("Job Board Monitor: starting scan...")
    summary: dict[str, Any] = {
        "jobs_scraped": 0,
        "companies_found": 0,
        "leads_upgraded": 0,
        "signals_created": 0,
        "errors": 0,
    }

    # ── Fetch all job postings ─────────────────────────────────
    all_jobs: list[dict[str, Any]] = []
    for job_title, url in INDEED_RSS_FEEDS.items():
        try:
            jobs = await fetch_indeed_rss(job_title, url)
            if not jobs:
                # Fallback to Google Custom Search
                jobs = await fetch_google_job_search(job_title)
            all_jobs.extend(jobs)
            summary["jobs_scraped"] += len(jobs)
        except Exception as exc:
            logger.error(f"Job board monitor error for '{job_title}': {exc}")
            summary["errors"] += 1

    if not all_jobs:
        logger.info("Job Board Monitor: no jobs found. Scan complete.")
        return summary

    # Deduplicate by company name
    seen_companies: dict[str, dict[str, Any]] = {}
    for job in all_jobs:
        cname = job["company_name"]
        if cname not in seen_companies:
            seen_companies[cname] = job

    summary["companies_found"] = len(seen_companies)
    logger.info(f"Job Board Monitor: {len(seen_companies)} unique companies from {len(all_jobs)} jobs")

    # ── Process against database ───────────────────────────────
    async with AsyncSessionLocal() as db:
        try:
            users_with_icps = await _get_active_users_with_icps(db)

            for cname, job in seen_companies.items():
                signal_config = JOB_SIGNALS.get(job["job_title"], {})
                if not signal_config:
                    continue

                company = await _find_company_by_name(db, cname)
                if company:
                    # Update company hiring status
                    company.is_hiring = True
                    company.job_posting_count = (company.job_posting_count or 0) + 1
                    await db.flush()

                    for user, icps in users_with_icps:
                        try:
                            lead = await _find_existing_lead(db, user.id, company.id)
                            if lead:
                                old_score = lead.lead_score or 0
                                new_score = min(100, old_score + signal_config["score_boost"])
                                lead.lead_score = new_score
                                if new_score >= 85:
                                    lead.lead_tier = LeadTier.HOT
                                elif new_score >= 60:
                                    lead.lead_tier = LeadTier.WARM

                                signals = list(lead.intent_signals or [])
                                if signal_config["signal"] not in signals:
                                    signals.append(signal_config["signal"])
                                lead.intent_signals = signals

                                note_addition = (
                                    f"\n\n[Job Board {datetime.now(timezone.utc).strftime('%Y-%m-%d')}] "
                                    f"{signal_config['why_now']}"
                                )
                                lead.notes = (lead.notes or "") + note_addition
                                if not lead.recommended_product:
                                    lead.recommended_product = signal_config["product"]

                                await db.flush()

                                hist = ZLLeadHistory(
                                    lead_id=lead.id,
                                    event_type="signal_detected",
                                    old_value=str(old_score),
                                    new_value=str(new_score),
                                    note=f"Job board signal: {signal_config['signal']} (+{signal_config['score_boost']})",
                                    created_by="system",
                                )
                                db.add(hist)
                                await db.flush()

                                summary["leads_upgraded"] += 1

                                await _create_auto_signal(
                                    db,
                                    user_id=user.id,
                                    company_id=company.id,
                                    lead_id=lead.id,
                                    company_name=company.name,
                                    signal_source="job_board_monitor",
                                    signal_type=signal_config["signal"],
                                    why_now=signal_config["why_now"],
                                    insurance_need=signal_config["product"],
                                    recommended_product=signal_config["product"],
                                    source_url=job.get("url"),
                                )
                                summary["signals_created"] += 1

                            else:
                                # Company exists but no lead for this user — create signal only
                                await _create_auto_signal(
                                    db,
                                    user_id=user.id,
                                    company_id=company.id,
                                    lead_id=None,
                                    company_name=company.name,
                                    signal_source="job_board_monitor",
                                    signal_type=signal_config["signal"],
                                    why_now=signal_config["why_now"],
                                    insurance_need=signal_config["product"],
                                    recommended_product=signal_config["product"],
                                    source_url=job.get("url"),
                                )
                                summary["signals_created"] += 1

                        except Exception as exc:
                            logger.error(f"Job board user {user.id} processing error: {exc}")
                            summary["errors"] += 1
                            continue
                else:
                    # Company not in DB — log for next scrape cycle
                    logger.info(f"Job Board: company '{cname}' not in DB, flagging for future scrape")
                    for user, icps in users_with_icps:
                        await _create_auto_signal(
                            db,
                            user_id=user.id,
                            company_id=None,
                            lead_id=None,
                            company_name=cname,
                            signal_source="job_board_monitor",
                            signal_type=signal_config["signal"],
                            why_now=signal_config["why_now"],
                            insurance_need=signal_config["product"],
                            recommended_product=signal_config["product"],
                            source_url=job.get("url"),
                        )
                        summary["signals_created"] += 1

            await db.commit()

        except Exception as exc:
            await db.rollback()
            logger.exception(f"Job Board Monitor database error: {exc}")
            summary["errors"] += 1

    logger.info(
        f"Job Board Monitor: scan complete. "
        f"jobs={summary['jobs_scraped']}, companies={summary['companies_found']}, "
        f"upgraded={summary['leads_upgraded']}, signals={summary['signals_created']}, "
        f"errors={summary['errors']}"
    )
    return summary
