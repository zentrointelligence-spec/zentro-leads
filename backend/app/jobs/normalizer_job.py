"""
Nightly bulk normalization job — Gemini Flash-Lite powered.

Runs at 3:00 AM via APScheduler. Processes all un-normalized or stale
records in batches of 100 to stay within Gemini context limits.

Five passes per run:
  A. Industry normalization  → ZLCompany.industry (standardized)
  B. Job title normalization → ZLPerson.job_title (clean) + seniority + department
  C. Location normalization  → ZLCompany.city / state / country / market
  D. Lead market tag         → ZLLead.market (from normalized company location)
  E. Insurance need          → ZLLead.insurance_type (B2B leads with no type set)

All DB writes are batched — a single commit per pass to minimize locking.
Any single pass failure is caught and logged; the job continues with remaining passes.
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gemini_client import (
    classify_insurance_needs_bulk,
    normalize_industries_bulk,
    normalize_job_titles_bulk,
    normalize_locations_bulk,
)
from app.database import AsyncSessionLocal
from app.models import ZLCompany, ZLLead, ZLPerson

# ── Batch size — Gemini can handle much larger, but 100 keeps
# prompts well within context limits for the cheapest model tier
BATCH_SIZE = 100


async def _normalize_industries(db: AsyncSession) -> int:
    """
    Normalize raw industry strings in ZLCompany to standard categories.

    Targets companies whose industry is non-null (raw scraped strings that
    haven't been standardized yet). Runs in batches of BATCH_SIZE.

    Returns:
        Number of company records updated.
    """
    result = await db.execute(
        select(ZLCompany.id, ZLCompany.industry)
        .where(ZLCompany.industry.isnot(None))
        .where(ZLCompany.industry != "")
    )
    rows = result.fetchall()

    if not rows:
        logger.info("[normalizer] No industries to normalize")
        return 0

    updated_count = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]
        raw_industries = [row.industry for row in batch]

        try:
            normalized_map = await normalize_industries_bulk(raw_industries)
        except Exception as exc:
            logger.error(f"[normalizer] Industry API call failed (batch {batch_start}): {exc}")
            continue

        for row in batch:
            normalized = normalized_map.get(row.industry)
            if normalized and normalized != row.industry:
                await db.execute(
                    update(ZLCompany)
                    .where(ZLCompany.id == row.id)
                    .values(industry=normalized)
                )
                updated_count += 1

        logger.debug(
            f"[normalizer] Industry batch {batch_start}–{batch_start + len(batch)}: "
            f"{updated_count} updated so far"
        )

    await db.commit()
    logger.info(f"[normalizer] Industry normalization done: {updated_count} companies updated")
    return updated_count


async def _normalize_job_titles(db: AsyncSession) -> int:
    """
    Normalize raw job title strings in ZLPerson.

    Also backfills seniority and department fields which are often empty
    after scraping. Updates is_decision_maker-equivalent via seniority field.

    Returns:
        Number of person records updated.
    """
    result = await db.execute(
        select(ZLPerson.id, ZLPerson.job_title)
        .where(ZLPerson.job_title.isnot(None))
        .where(ZLPerson.job_title != "")
    )
    rows = result.fetchall()

    if not rows:
        logger.info("[normalizer] No job titles to normalize")
        return 0

    updated_count = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]
        raw_titles = [row.job_title for row in batch]

        try:
            normalized_map = await normalize_job_titles_bulk(raw_titles)
        except Exception as exc:
            logger.error(f"[normalizer] Job title API call failed (batch {batch_start}): {exc}")
            continue

        for row in batch:
            meta: dict[str, Any] = normalized_map.get(row.job_title, {})
            if not meta:
                continue

            await db.execute(
                update(ZLPerson)
                .where(ZLPerson.id == row.id)
                .values(
                    job_title  = meta.get("normalized", row.job_title),
                    seniority  = meta.get("seniority",  "unknown"),
                    department = meta.get("department", "Unknown"),
                )
            )
            updated_count += 1

        logger.debug(
            f"[normalizer] Job title batch {batch_start}–{batch_start + len(batch)}: "
            f"{updated_count} updated so far"
        )

    await db.commit()
    logger.info(f"[normalizer] Job title normalization done: {updated_count} people updated")
    return updated_count


async def _normalize_locations(db: AsyncSession) -> tuple[int, int]:
    """
    Normalize raw location strings in ZLCompany, then cascade market tag to ZLLead.

    Updates ZLCompany.city / state / country, then marks ZLLead.market for any
    lead linked to that company — avoiding a separate location query per lead.

    Returns:
        Tuple of (companies_updated, leads_tagged).
    """
    result = await db.execute(
        select(ZLCompany.id, ZLCompany.city, ZLCompany.state, ZLCompany.country)
        .where(ZLCompany.city.isnot(None))
        .where(ZLCompany.city != "")
    )
    rows = result.fetchall()

    if not rows:
        logger.info("[normalizer] No locations to normalize")
        return 0, 0

    companies_updated = 0
    leads_tagged = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]
        # Use full "city, state, country" string as the normalization input
        raw_locations: list[str] = []
        for row in batch:
            parts = [p for p in [row.city, row.state, row.country] if p]
            raw_locations.append(", ".join(parts) if parts else row.city)

        try:
            normalized_map = await normalize_locations_bulk(raw_locations)
        except Exception as exc:
            logger.error(f"[normalizer] Location API call failed (batch {batch_start}): {exc}")
            continue

        for row, raw_loc in zip(batch, raw_locations):
            loc = normalized_map.get(raw_loc)
            if not loc:
                continue

            await db.execute(
                update(ZLCompany)
                .where(ZLCompany.id == row.id)
                .values(
                    city    = loc.get("city",    row.city),
                    state   = loc.get("state",   row.state),
                    country = loc.get("country", row.country),
                )
            )
            companies_updated += 1

            # Cascade market tag to all leads linked to this company
            market = loc.get("market", "other")
            if market in ("malaysia", "india"):
                result_leads = await db.execute(
                    update(ZLLead)
                    .where(ZLLead.company_id == row.id)
                    .where(ZLLead.market.is_(None))
                    .values(market=market)
                    .returning(ZLLead.id)
                )
                leads_tagged += len(result_leads.fetchall())

    await db.commit()
    logger.info(
        f"[normalizer] Location normalization done: "
        f"{companies_updated} companies updated, {leads_tagged} leads tagged"
    )
    return companies_updated, leads_tagged


async def _classify_insurance_needs(db: AsyncSession) -> int:
    """
    Classify insurance needs for B2B leads that have no insurance_type set.

    Builds a description dict for each lead using company data and signals,
    then calls Gemini to classify the most likely insurance product.

    Returns:
        Number of leads updated.
    """
    # Fetch leads with no insurance_type, joined with company data
    result = await db.execute(
        select(
            ZLLead.id,
            ZLLead.intent_signals,
            ZLCompany.industry,
            ZLCompany.employee_count,
            ZLCompany.employee_range,
        )
        .join(ZLCompany, ZLLead.company_id == ZLCompany.id, isouter=True)
        .where(ZLLead.insurance_type.is_(None))
        .where(ZLLead.company_id.isnot(None))
    )
    rows = result.fetchall()

    if not rows:
        logger.info("[normalizer] No leads need insurance classification")
        return 0

    updated_count = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]

        lead_descriptions: list[dict[str, Any]] = []
        for row in batch:
            signals = row.intent_signals or []
            lead_descriptions.append({
                "id":           row.id,
                "company_type": row.industry or "unknown",
                "size":         row.employee_count or row.employee_range or "unknown",
                "signals":      signals[:5],  # Limit tokens
            })

        try:
            classified = await classify_insurance_needs_bulk(lead_descriptions)
        except Exception as exc:
            logger.error(f"[normalizer] Insurance classification failed (batch {batch_start}): {exc}")
            continue

        for lead_id, insurance_type in classified.items():
            if insurance_type and insurance_type != "other":
                await db.execute(
                    update(ZLLead)
                    .where(ZLLead.id == lead_id)
                    .values(insurance_type=insurance_type)
                )
                updated_count += 1

        logger.debug(
            f"[normalizer] Insurance batch {batch_start}–{batch_start + len(batch)}: "
            f"{updated_count} classified so far"
        )

    await db.commit()
    logger.info(f"[normalizer] Insurance classification done: {updated_count} leads updated")
    return updated_count


# ═══════════════════════════════════════════════════════════════════════════════
# Public entry point
# ═══════════════════════════════════════════════════════════════════════════════

async def run_bulk_normalization() -> dict[str, int]:
    """
    Run all four normalization passes against the full database.

    Designed to be called by APScheduler (nightly 3 AM) or the manual
    POST /leads/normalize endpoint. Uses its own DB session lifecycle.

    Each pass is wrapped in individual try/except so a Gemini API error
    in one pass does not abort the others.

    Returns:
        Summary dict with counts for each pass, e.g.:
        {
            "industries_updated": 42,
            "titles_updated":     87,
            "locations_updated":  31,
            "leads_market_tagged": 56,
            "insurance_classified": 19,
        }
    """
    logger.info("[normalizer] Starting nightly bulk normalization run")
    summary: dict[str, int] = {
        "industries_updated":    0,
        "titles_updated":        0,
        "locations_updated":     0,
        "leads_market_tagged":   0,
        "insurance_classified":  0,
    }

    # Pass A — Industry
    try:
        async with AsyncSessionLocal() as db:
            summary["industries_updated"] = await _normalize_industries(db)
    except Exception as exc:
        logger.error(f"[normalizer] Industry pass failed: {exc}")

    # Pass B — Job titles
    try:
        async with AsyncSessionLocal() as db:
            summary["titles_updated"] = await _normalize_job_titles(db)
    except Exception as exc:
        logger.error(f"[normalizer] Job title pass failed: {exc}")

    # Pass C+D — Locations + market cascade
    try:
        async with AsyncSessionLocal() as db:
            companies_updated, leads_tagged = await _normalize_locations(db)
            summary["locations_updated"]   = companies_updated
            summary["leads_market_tagged"] = leads_tagged
    except Exception as exc:
        logger.error(f"[normalizer] Location pass failed: {exc}")

    # Pass E — Insurance needs
    try:
        async with AsyncSessionLocal() as db:
            summary["insurance_classified"] = await _classify_insurance_needs(db)
    except Exception as exc:
        logger.error(f"[normalizer] Insurance classification pass failed: {exc}")

    logger.info(
        f"[normalizer] Bulk normalization complete — "
        + ", ".join(f"{k}: {v}" for k, v in summary.items())
    )
    return summary
