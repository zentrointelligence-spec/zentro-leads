"""
SSM Monitor — Detect newly registered Malaysian companies.
New companies need ALL insurance from scratch = highest intent signal.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import func, select

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
# Search Queries
# ═══════════════════════════════════════════════════════════════

SSM_SEARCH_QUERIES: list[str] = [
    "new company registered Malaysia logistics sdn bhd 2026",
    "syarikat baru ditubuhkan pembinaan Malaysia 2026",
    "new sdn bhd registered construction Malaysia 2026",
    "new transport company registered Malaysia 2026",
    "new manufacturing company Malaysia sdn bhd 2026",
    "new warehouse company registered Malaysia 2026",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ═══════════════════════════════════════════════════════════════
# Google Custom Search
# ═══════════════════════════════════════════════════════════════


async def _google_search(query: str) -> list[dict[str, Any]]:
    """Run a single Google Custom Search query."""
    if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_CX:
        return []

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
        logger.warning(f"SSM Google search failed: {exc}")
        return []

    results: list[dict[str, Any]] = []
    for item in data.get("items", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")

        # Extract company name from title
        company_name = _extract_company_from_search(title, snippet)
        if company_name and len(company_name) >= 3:
            results.append({
                "company_name": company_name,
                "title": title,
                "snippet": snippet,
                "url": link,
                "query": query,
            })

    return results


def _extract_company_from_search(title: str, snippet: str) -> str | None:
    """Extract company name from Google search result."""
    text = title or ""

    # Pattern: "Company Name Sdn Bhd" or "Company Name Bhd"
    match = re.search(r"([A-Z][A-Za-z0-9\s&]+(?:Sdn\s+Bhd|Bhd|Ltd|Group))", text)
    if match:
        return match.group(1).strip()

    # Pattern: "Company Name — ..."
    parts = text.split("—", 1)
    if len(parts) == 2:
        candidate = parts[0].strip()
        if len(candidate) >= 3 and len(candidate) <= 80:
            return candidate

    # Pattern: first 2-4 words before common separators
    clean = re.sub(r"\s*[-|–].*$", "", text)
    words = clean.split()
    if len(words) >= 2:
        candidate = " ".join(words[:4]).strip()
        if len(candidate) >= 3:
            return candidate

    return None


# ═══════════════════════════════════════════════════════════════
# Database Operations
# ═══════════════════════════════════════════════════════════════


async def _find_company_by_name(db, name: str) -> ZLCompany | None:
    if not name or len(name) < 3:
        return None
    result = await db.execute(
        select(ZLCompany).where(func.lower(ZLCompany.name) == name.lower())
    )
    company = result.scalar_one_or_none()
    if company:
        return company
    result = await db.execute(
        select(ZLCompany).where(func.lower(ZLCompany.name).like(f"%{name.lower()}%")).limit(1)
    )
    return result.scalar_one_or_none()


async def _get_active_users_with_icps(db):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(ZLUser).where(ZLUser.is_active == True).options(selectinload(ZLUser.icps))
    )
    users = result.scalars().unique().all()
    return [(u, [i for i in u.icps if i.is_active]) for u in users if u.icps]


# ═══════════════════════════════════════════════════════════════
# Main Job
# ═══════════════════════════════════════════════════════════════


async def run_ssm_monitor() -> dict[str, Any]:
    """
    SSM Monitor — daily at 6 AM.
    Finds newly registered Malaysian companies and creates WARM leads.
    """
    logger.info("SSM Monitor: starting scan...")
    summary: dict[str, Any] = {
        "queries_run": 0,
        "companies_found": 0,
        "new_companies": 0,
        "leads_created": 0,
        "signals_created": 0,
        "errors": 0,
    }

    # ── Fetch search results ───────────────────────────────────
    all_results: list[dict[str, Any]] = []
    for query in SSM_SEARCH_QUERIES:
        try:
            results = await _google_search(query)
            all_results.extend(results)
            summary["queries_run"] += 1
        except Exception as exc:
            logger.error(f"SSM query '{query}' error: {exc}")
            summary["errors"] += 1

    # Deduplicate
    seen: dict[str, dict[str, Any]] = {}
    for r in all_results:
        cname = r["company_name"]
        if cname not in seen:
            seen[cname] = r

    summary["companies_found"] = len(seen)
    logger.info(f"SSM Monitor: {len(seen)} unique companies from search")

    if not seen:
        logger.info("SSM Monitor: no companies found. Scan complete.")
        return summary

    # ── Database operations ────────────────────────────────────
    async with AsyncSessionLocal() as db:
        try:
            users_with_icps = await _get_active_users_with_icps(db)
            current_year = datetime.now(timezone.utc).year

            for cname, result in seen.items():
                company = await _find_company_by_name(db, cname)
                if company:
                    logger.debug(f"SSM: company '{cname}' already exists")
                    continue

                summary["new_companies"] += 1

                # Create new company
                company = ZLCompany(
                    name=cname,
                    industry="Unknown",  # Will be enriched later
                    country="Malaysia",
                    founded_year=current_year,
                    data_source=LeadSource.GOVERNMENT,
                )
                db.add(company)
                await db.flush()

                # Create synthetic person
                person = ZLPerson(
                    company_id=company.id,
                    full_name="Decision Maker",
                    first_name="Decision",
                    last_name="Maker",
                    job_title="Director",
                    seniority="director",
                    data_source=LeadSource.GOVERNMENT,
                )
                db.add(person)
                await db.flush()

                why_now = (
                    "Newly registered company — needs all insurance coverage from scratch. "
                    "No existing insurer relationship. Prime opportunity for first-mover advantage."
                )

                for user, icps in users_with_icps:
                    try:
                        primary_icp = icps[0] if icps else None

                        # Check limit
                        current_used = user.leads_used_this_month or 0
                        current_limit = user.leads_limit or 0
                        if current_limit > 0 and current_used >= current_limit:
                            continue

                        lead = ZLLead(
                            user_id=user.id,
                            icp_id=primary_icp.id if primary_icp else None,
                            person_id=person.id,
                            company_id=company.id,
                            lead_score=70,
                            lead_tier=LeadTier.WARM,
                            score_breakdown={
                                "company_size": 0,
                                "role": 0,
                                "industry": 0,
                                "signals": 0,
                                "email": 0,
                                "icp_bonus": 0,
                                "email_bonus": 0,
                                "new_company_boost": 70,
                            },
                            intent_signals=["new_registration"],
                            status=LeadStatus.NEW,
                            source=LeadSource.GOVERNMENT,
                            notes=why_now,
                            icp_match_score=60,
                            icp_verdict="New company",
                            icp_reason="Recently registered — no existing insurance relationships",
                            recommended_product="Complete Business Insurance Package",
                        )
                        db.add(lead)
                        await db.flush()

                        await db.execute(
                            select(ZLUser).where(ZLUser.id == user.id)
                        )
                        await db.execute(
                            update(ZLUser)
                            .where(ZLUser.id == user.id)
                            .values(leads_used_this_month=func.coalesce(ZLUser.leads_used_this_month, 0) + 1)
                        )

                        hist = ZLLeadHistory(
                            lead_id=lead.id,
                            event_type="signal_detected",
                            new_value="warm",
                            note="Created from SSM Monitor: newly registered company",
                            created_by="system",
                        )
                        db.add(hist)

                        await _create_signal_record(
                            db, user.id, company.id, lead.id, cname, result["url"]
                        )
                        summary["leads_created"] += 1
                        summary["signals_created"] += 1

                    except Exception as exc:
                        logger.error(f"SSM user {user.id} processing error: {exc}")
                        summary["errors"] += 1
                        continue

            await db.commit()

        except Exception as exc:
            await db.rollback()
            logger.exception(f"SSM Monitor database error: {exc}")
            summary["errors"] += 1

    logger.info(
        f"SSM Monitor: scan complete. "
        f"queries={summary['queries_run']}, new_companies={summary['new_companies']}, "
        f"leads={summary['leads_created']}, errors={summary['errors']}"
    )
    return summary


async def _create_signal_record(
    db, user_id: str, company_id: str, lead_id: str, company_name: str, url: str | None
) -> None:
    signal = ZLAutoSignal(
        user_id=user_id,
        company_id=company_id,
        lead_id=lead_id,
        company_name=company_name,
        signal_source="ssm_monitor",
        signal_type="new_registration",
        signal_detail="Company registered recently — no existing insurance",
        why_now="Newly registered company needs all insurance from scratch",
        insurance_need="Complete Business Insurance Package",
        recommended_product="Complete Business Insurance Package",
        source_url=url,
        confidence=0.7,
    )
    db.add(signal)
    await db.flush()
