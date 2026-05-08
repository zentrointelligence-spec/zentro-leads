"""Leads API routes — generation, listing, stats, NL search, ZIMS push."""

from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime, UTC
from typing import Any, Optional

from anthropic import AsyncAnthropic
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.utils import get_current_user, require_admin
from app.config import settings
from app.database import get_db
from app.leads.generator import run_lead_generation_job
from app.leads.b2c_generator import (
    run_b2c_vehicle_job,
    run_b2c_property_job,
    run_b2c_india_property_job,
)
from app.leads.schemas import (
    GenerateLeadsRequest,
    GenerateLeadsResponse,
    ICPMatchDetail,
    LeadListResponse,
    LeadNoteUpdate,
    LeadResponse,
    LeadStatsResponse,
    LeadStatusUpdate,
    NLSearchRequest,
    OutreachRequest,
    ScoreBreakdownResponse,
    ScoreFactor,
    SheetsExportRequest,
)
from app.models import (
    LeadStatus,
    LeadTier,
    ZLCompany,
    ZLExport,
    ZLICP,
    ZLLead,
    ZLLeadHistory,
    ZLPerson,
    ZLSuppressionList,
    ZLUser,
)
from app.analytics.tracker import track_lead_viewed, track_reply_received, track_deal_closed
from app.sync.zims import push_lead_to_zims
from app.rate_limiter import limiter

router = APIRouter()


async def get_current_user_dep(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> ZLUser:
    """Dependency wrapper around ``get_current_user`` with DB injection."""
    return await get_current_user(zentro_session=zentro_session, db=db)


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.lower().startswith("json"):
                inner = inner[4:]
            return inner.strip()
    return text


@limiter.limit("3/minute")
@router.post("/generate", response_model=GenerateLeadsResponse, status_code=202)
async def generate_leads(
    request: Request,
    body: GenerateLeadsRequest,
    background_tasks: BackgroundTasks,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue full lead generation for an ICP.

    Returns immediately; work runs in a background task with its own DB session.
    """
    icp = await db.get(ZLICP, body.icp_id)
    if not icp or icp.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ICP not found.")

    if user.leads_used_this_month >= user.leads_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Monthly lead limit reached",
                "used": user.leads_used_this_month,
                "limit": user.leads_limit,
                "upgrade_url": "/dashboard/billing",
            },
        )

    # Note: the actual atomic limit enforcement happens inside
    # run_lead_generation_job so concurrent jobs cannot overshoot.
    lead_type = (body.lead_type or "b2b").lower()

    if lead_type in ("b2b", "both"):
        background_tasks.add_task(run_lead_generation_job, user.id, body.icp_id)

    if lead_type in ("b2c", "both"):
        market         = (getattr(body, "market", None) or "malaysia").lower()
        insurance_type = getattr(body, "insurance_type", None)

        # Build a minimal ICP dict for the B2C generators.
        icp_dict = {
            "market":         market,
            "locations":      icp.locations or (["India"] if market == "india" else ["Malaysia"]),
            "age_ranges":     [],
            "income_brackets": [],
            "life_events":    ["new_vehicle", "new_property"],
        }

        # Motor insurance leads — always run for B2C (market-aware)
        background_tasks.add_task(run_b2c_vehicle_job, user.id, icp_dict, 50)

        # Home insurance leads
        if insurance_type in (None, "home"):
            if market == "india":
                background_tasks.add_task(run_b2c_india_property_job, user.id, icp_dict, 50)
            else:
                background_tasks.add_task(run_b2c_property_job, user.id, icp_dict, 50)

    mode_label = {"b2b": "B2B", "b2c": "B2C", "both": "B2B + B2C"}.get(lead_type, "B2B")
    return GenerateLeadsResponse(
        message=f"{mode_label} lead generation started. Results will appear shortly.",
        estimated_seconds=90 if lead_type == "b2b" else 120,
        icp_name=icp.name,
    )


@limiter.limit("30/minute")
@router.get("/stats", response_model=LeadStatsResponse)
async def lead_stats(
    request: Request,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregate lead counts and plan usage for the current user."""
    rows = await db.execute(
        select(ZLLead.lead_tier, func.count())
        .where(ZLLead.user_id == user.id)
        .group_by(ZLLead.lead_tier)
    )
    counts: dict[str, int] = {t.value: 0 for t in LeadTier}
    for tier, cnt in rows.all():
        if tier is None:
            continue
        key = tier.value if isinstance(tier, LeadTier) else str(tier).lower()
        counts[key] = int(cnt)

    total_res = await db.execute(select(func.count()).select_from(ZLLead).where(ZLLead.user_id == user.id))
    total = int(total_res.scalar_one() or 0)

    limit = max(user.leads_limit, 1)
    used = user.leads_used_this_month or 0
    pct = min(100.0, round(100.0 * used / limit, 2))

    return LeadStatsResponse(
        hot=counts.get("hot", 0),
        warm=counts.get("warm", 0),
        potential=counts.get("potential", 0),
        cold=counts.get("cold", 0),
        total=total,
        used_this_month=used,
        limit=user.leads_limit,
        limit_percentage=pct,
    )


@limiter.limit("60/minute")
@router.get("/", response_model=LeadListResponse)
async def list_leads(
    request: Request,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
    tier: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    icp_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    has_email: Optional[bool] = Query(default=None),
    zims_synced: Optional[bool] = Query(default=None),
    min_icp_match: Optional[int] = Query(default=None, ge=0, le=100),
    lead_type: Optional[str] = Query(default=None),
    market: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """Paginated list of leads with optional filters."""
    filters: list[Any] = [ZLLead.user_id == user.id]

    if tier:
        try:
            filters.append(ZLLead.lead_tier == LeadTier[tier.upper()])
        except KeyError:
            raise HTTPException(status_code=422, detail="Invalid tier filter.")

    if status_filter:
        try:
            filters.append(ZLLead.status == LeadStatus[status_filter.upper()])
        except KeyError:
            raise HTTPException(status_code=422, detail="Invalid status filter.")

    if icp_id:
        filters.append(ZLLead.icp_id == icp_id)

    if has_email is True:
        filters.append(ZLPerson.email.isnot(None))
        filters.append(ZLPerson.email != "")
    elif has_email is False:
        filters.append(
            or_(ZLPerson.id.is_(None), ZLPerson.email.is_(None), ZLPerson.email == "")
        )

    if zims_synced is True:
        filters.append(ZLLead.zims_lead_id.isnot(None))
        filters.append(ZLLead.zims_lead_id != "")
    elif zims_synced is False:
        filters.append(or_(ZLLead.zims_lead_id.is_(None), ZLLead.zims_lead_id == ""))

    if min_icp_match is not None:
        filters.append(
            or_(ZLLead.icp_match_score >= min_icp_match, ZLLead.icp_match_score.is_(None))
        )

    if lead_type and lead_type in ("b2b", "b2c"):
        filters.append(ZLLead.lead_type == lead_type)

    if market and market in ("malaysia", "india"):
        filters.append(ZLLead.market == market)

    search_like: str | None = None
    if search:
        search_like = f"%{search.lower()}%"

    stmt = (
        select(ZLLead)
        .outerjoin(ZLPerson, ZLPerson.id == ZLLead.person_id)
        .outerjoin(ZLCompany, ZLCompany.id == ZLLead.company_id)
        .where(*filters)
    )
    if search_like:
        stmt = stmt.where(
            or_(
                func.lower(ZLLead.notes).like(search_like),
                func.lower(ZLPerson.full_name).like(search_like),
                func.lower(ZLPerson.email).like(search_like),
                func.lower(ZLCompany.name).like(search_like),
                func.lower(ZLCompany.industry).like(search_like),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    offset = (page - 1) * per_page
    stmt = (
        stmt.options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .order_by(ZLLead.lead_score.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    leads = result.scalars().unique().all()

    pages = math.ceil(total / per_page) if per_page else 0
    items = [LeadResponse.model_validate(l) for l in leads]
    return LeadListResponse(items=items, total=total, page=page, per_page=per_page, pages=pages)


@limiter.limit("30/minute")
@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    request: Request,
    lead_id: str,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Return a single lead with nested person and company."""
    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.id == lead_id, ZLLead.user_id == user.id)
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    # Track lead_viewed event (deduped per user+lead in tracker)
    await track_lead_viewed(db, lead_id, str(user.id))

    return LeadResponse.model_validate(lead)


@limiter.limit("20/minute")
@router.get("/{lead_id}/score-breakdown", response_model=ScoreBreakdownResponse)
async def get_score_breakdown(
    request: Request,
    lead_id: str,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a detailed, human-readable score breakdown for a single lead.

    Includes per-factor awarded/possible points, an AI explanation from
    GPT-4o Mini, ICP dimension flags, and the detected intent signals.
    Result is cached in Redis for 1 hour.
    """
    from app.ai.gpt_client import generate_score_explanation
    from app.redis_client import get_cached, set_cached

    cache_key = f"score_breakdown:{lead_id}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    # ── Load lead ─────────────────────────────────────────────────────────────
    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.id == lead_id, ZLLead.user_id == user.id)
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    person  = lead.person
    company = lead.company
    bd      = dict(lead.score_breakdown or {})

    # ── Build score factors ───────────────────────────────────────────────────
    cname    = str(company.name)    if company and company.name    is not None else "Unknown"
    industry = str(company.industry)if company and company.industry is not None else None
    emp_rng  = str(company.employee_range) if company and company.employee_range is not None else None
    city     = str(company.city)    if company and company.city    is not None else ""
    country  = str(company.country) if company and company.country is not None else ""
    location = f"{city}, {country}".strip(", ") or None
    job_title= str(person.job_title)if person  and person.job_title is not None else None
    signals: list[str] = list(lead.intent_signals or [])

    cs_pts  = int(bd.get("company_size",  0))
    ro_pts  = int(bd.get("role",          0))
    ind_pts = int(bd.get("industry",      0))
    sig_pts = int(bd.get("signals",       0))
    em_pts  = int(bd.get("email",         0))
    icp_pts = int(bd.get("icp_match_bonus", 0))

    factors: list[ScoreFactor] = [
        ScoreFactor(
            name="Company Size Match",
            points_awarded=cs_pts,
            points_possible=30,
            met=cs_pts > 0,
            reason=(
                f"{cname} has {emp_rng or 'unknown'} employees"
                + (" — within ICP range." if cs_pts == 30 else " — partial match to ICP range." if cs_pts > 0 else " — outside ICP range.")
            ),
        ),
        ScoreFactor(
            name="Role Match",
            points_awarded=ro_pts,
            points_possible=25,
            met=ro_pts > 0,
            reason=(
                f"{job_title or 'Unknown role'}"
                + (" — exact ICP title match." if ro_pts == 25 else " — partial seniority match." if ro_pts > 0 else " — role does not match ICP criteria.")
            ),
        ),
        ScoreFactor(
            name="Industry Match",
            points_awarded=ind_pts,
            points_possible=20,
            met=ind_pts > 0,
            reason=(
                f"{industry or 'Unknown industry'}"
                + (" — exact industry match." if ind_pts == 20 else " — related industry." if ind_pts > 0 else " — industry not in ICP target list.")
            ),
        ),
        ScoreFactor(
            name="Intent Signals",
            points_awarded=sig_pts,
            points_possible=15,
            met=sig_pts > 0,
            reason=(
                f"{len(signals)} signal(s) detected: {', '.join(signals)}" if signals else "No intent signals detected."
            ),
        ),
        ScoreFactor(
            name="Email Verified",
            points_awarded=em_pts,
            points_possible=10,
            met=em_pts > 0,
            reason=(
                "Email verified with high confidence." if em_pts == 10
                else "Email found but unverified." if em_pts > 0
                else "No verified email on file."
            ),
        ),
        ScoreFactor(
            name="ICP Match Bonus",
            points_awarded=icp_pts,
            points_possible=25,
            met=icp_pts > 0,
            reason=(
                f"ICP validation score: {lead.icp_match_score or 0}% — {lead.icp_verdict or 'No verdict'}"
            ),
        ),
    ]

    # ── ICP match flags ───────────────────────────────────────────────────────
    icp_match_pct = lead.icp_match_score or 0
    icp_detail = ICPMatchDetail(
        industry=ind_pts > 0,
        location=bool(location),
        company_size=cs_pts > 0,
        role=ro_pts > 0,
        overall_match_pct=icp_match_pct,
    )

    # ── AI explanation via GPT-4o Mini ────────────────────────────────────────
    tier = (lead.lead_tier.value if hasattr(lead.lead_tier, "value") else str(lead.lead_tier)).lower()
    lead_dict = {
        "company_name": cname,
        "lead_score":   lead.lead_score or 0,
        "lead_tier":    tier,
        "industry":     industry,
        "location":     location,
    }
    ai_explanation = await generate_score_explanation(lead_dict, bd)

    # ── Assemble response ─────────────────────────────────────────────────────
    breakdown = ScoreBreakdownResponse(
        total_score=lead.lead_score or 0,
        tier=tier.upper(),
        factors=factors,
        ai_explanation=ai_explanation,
        signals=signals,
        icp_match=icp_detail,
    )

    await set_cached(cache_key, breakdown.model_dump(), ttl=3600)
    return breakdown


@limiter.limit("30/minute")
@router.patch("/{lead_id}/status", response_model=LeadResponse)
async def update_lead_status(
    request: Request,
    lead_id: str,
    body: LeadStatusUpdate,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Update lead status and append a history row. Track conversion events."""
    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.id == lead_id, ZLLead.user_id == user.id)
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    old = lead.status.value if lead.status else None
    lead.status = body.status
    await db.flush()

    hist = ZLLeadHistory(
        lead_id=lead.id,
        event_type="status_change",
        old_value=old,
        new_value=body.status.value,
        created_by=user.id,
    )
    db.add(hist)
    await db.flush()

    # Track conversion events on status transitions
    if body.status.value == "replied":
        await track_reply_received(db, lead)
    elif body.status.value == "won":
        await track_deal_closed(db, lead)

    # Refresh to pick up server-generated updated_at before Pydantic serializes
    await db.refresh(lead)
    return LeadResponse.model_validate(lead)


@limiter.limit("30/minute")
@router.patch("/{lead_id}/note", response_model=LeadResponse)
async def update_lead_note(
    request: Request,
    lead_id: str,
    body: LeadNoteUpdate,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Replace lead notes and record history."""
    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.id == lead_id, ZLLead.user_id == user.id)
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    lead.notes = body.note
    await db.flush()

    hist = ZLLeadHistory(
        lead_id=lead.id,
        event_type="note_added",
        old_value=None,
        new_value=None,
        note=body.note,
        created_by=user.id,
    )
    db.add(hist)
    await db.flush()

    return LeadResponse.model_validate(lead)


@limiter.limit("10/minute")
@router.post("/{lead_id}/push-to-zims")
async def push_to_zims_endpoint(
    request: Request,
    lead_id: str,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger ZIMS push for a lead (non-blocking worker)."""
    res = await db.execute(select(ZLLead).where(ZLLead.id == lead_id, ZLLead.user_id == user.id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    await push_lead_to_zims(lead.id)

    await db.refresh(lead)
    return {"message": "ZIMS push requested.", "zims_lead_id": lead.zims_lead_id}


@limiter.limit("10/minute")
@router.post("/{lead_id}/outreach")
async def generate_outreach(
    request: Request,
    lead_id: str,
    body: OutreachRequest,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a GPT-4o Mini outreach draft for a specific lead.

    Results are cached in Redis for 24 h to avoid duplicate API calls.
    Cache key: zl:outreach:{lead_id}:{channel}:{language}
    """
    from app.ai.gpt_client import generate_outreach_draft
    from app.redis_client import get_cached, set_cached

    channel       = (body.channel or "whatsapp").lower()
    language      = (body.language or "en").lower()
    insurance_type = body.insurance_type or "insurance"

    # ── Cache check ───────────────────────────────────────────────────────────
    cache_key = f"outreach:{lead_id}:{channel}:{language}"
    cached = await get_cached(cache_key)
    if cached:
        logger.debug(f"Outreach: cache hit for lead {lead_id} / {channel} / {language}")
        return cached

    # ── Load lead ─────────────────────────────────────────────────────────────
    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.id == lead_id, ZLLead.user_id == user.id)
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    person  = lead.person
    company = lead.company

    city    = str(company.city)    if company and company.city    is not None else ""
    country = str(company.country) if company and company.country is not None else ""
    location = f"{city}, {country}".strip(", ") or "Malaysia"

    lead_dict = {
        "person_name":    str(person.full_name)  if person and person.full_name  is not None else "",
        "company_name":   str(company.name)      if company and company.name     is not None else "",
        "location":       location,
        "intent_signals": list(lead.intent_signals or []),
        "icp_reason":     str(lead.icp_reason)   if lead.icp_reason is not None else "",
        "lead_score":     lead.lead_score or 0,
    }

    # ── Generate draft ────────────────────────────────────────────────────────
    draft = await generate_outreach_draft(
        lead=lead_dict,
        channel=channel,
        language=language,
        insurance_type=insurance_type,
    )

    # ── Cache for 24 h ────────────────────────────────────────────────────────
    await set_cached(cache_key, draft, ttl=86_400)
    logger.debug(f"Outreach: generated + cached for lead {lead_id} / {channel} / {language}")

    return draft


@router.post("/{lead_id}/suppress")
async def suppress_lead(
    request: Request,
    lead_id: str,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Suppress a lead's contact channels: add email/domain to suppression list
    and mark the lead as suppressed.
    """
    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.id == lead_id, ZLLead.user_id == user.id)
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    if lead.person and lead.person.email:
        em = lead.person.email.lower().strip()
        existing = await db.execute(
            select(ZLSuppressionList).where(
                ZLSuppressionList.value == em,
                ZLSuppressionList.value_type == "email",
                or_(ZLSuppressionList.user_id == user.id, ZLSuppressionList.user_id.is_(None)),
            )
        )
        if not existing.scalar_one_or_none():
            db.add(
                ZLSuppressionList(
                    user_id=user.id,
                    value=em,
                    value_type="email",
                    reason="user_suppressed",
                )
            )

    if lead.company and lead.company.domain:
        dom = lead.company.domain.lower().strip()
        existing_d = await db.execute(
            select(ZLSuppressionList).where(
                ZLSuppressionList.value == dom,
                ZLSuppressionList.value_type == "domain",
                or_(ZLSuppressionList.user_id == user.id, ZLSuppressionList.user_id.is_(None)),
            )
        )
        if not existing_d.scalar_one_or_none():
            db.add(
                ZLSuppressionList(
                    user_id=user.id,
                    value=dom,
                    value_type="domain",
                    reason="user_suppressed",
                )
            )

    old_status = lead.status.value if lead.status else None
    lead.status = LeadStatus.SUPPRESSED
    await db.flush()

    db.add(
        ZLLeadHistory(
            lead_id=lead.id,
            event_type="suppressed",
            old_value=old_status,
            new_value=LeadStatus.SUPPRESSED.value,
            created_by=user.id,
        )
    )
    await db.flush()

    return {"message": "Lead suppressed and added to your suppression list."}


@limiter.limit("10/minute")
@router.post("/search/nl", response_model=list[LeadResponse])
async def nl_search(
    request: Request,
    body: NLSearchRequest,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Hybrid natural-language lead search.

    Runs PostgreSQL (structured filters), Elasticsearch (full-text), and
    Pinecone (semantic/vector) searches in parallel, merges and re-ranks
    the results, then hydrates the top leads from PostgreSQL before
    returning them in the standard LeadResponse format.
    """
    from app.search.hybrid_merger import hybrid_lead_search

    query = (body.query or "").strip()
    if not query:
        return []

    limit = min(int(getattr(body, "limit", 50) or 50), 100)

    # ── 1. Run hybrid search → ordered list of {lead_id, final_score, …} ──────
    ranked = await hybrid_lead_search(
        query=query,
        user_id=str(user.id),
        db=db,
        limit=limit,
    )

    if not ranked:
        return []

    # ── 2. Hydrate full lead objects from PostgreSQL in final_score order ──────
    lead_ids: list[str] = [r["lead_id"] for r in ranked]

    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.user_id == user.id, ZLLead.id.in_(lead_ids))
    )
    leads_by_id: dict[str, ZLLead] = {
        str(l.id): l for l in res.scalars().unique().all()
    }

    # ── 3. Return in ranked order, skipping any ids not found in DB ───────────
    out: list[LeadResponse] = []
    for lead_id in lead_ids:
        lead = leads_by_id.get(lead_id)
        if lead:
            out.append(LeadResponse.model_validate(lead))

    return out


@limiter.limit("10/minute")
@router.post("/export/csv")
async def export_csv(
    request: Request,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Export all user leads as a CSV file."""
    res = await db.execute(
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.user_id == user.id)
        .order_by(ZLLead.lead_score.desc())
    )
    leads = res.scalars().unique().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "lead_id", "score", "tier", "status", "company_name", "industry",
        "person_name", "job_title", "email", "email_verified", "phone",
        "linkedin_url", "country", "city", "intent_signals", "notes",
        "created_at",
    ])

    for lead in leads:
        person = lead.person
        company = lead.company
        writer.writerow([
            lead.id,
            lead.lead_score,
            lead.lead_tier.value if lead.lead_tier else "",
            lead.status.value if lead.status else "",
            company.name if company else "",
            company.industry if company else "",
            person.full_name if person else "",
            person.job_title if person else "",
            person.email if person else "",
            person.email_verified if person else False,
            person.phone if person else "",
            person.linkedin_url if person else "",
            company.country if company else "",
            company.city if company else "",
            ", ".join(lead.intent_signals or []),
            (lead.notes or "").replace("\n", " "),
            lead.created_at.isoformat() if lead.created_at else "",
        ])

    output.seek(0)
    content = output.getvalue()
    output.close()

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@limiter.limit("3/hour")
@router.post("/retrain-model")
async def retrain_model(
    request: Request,
    model_type: str = "b2b",
    user: ZLUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger an immediate XGBoost model retrain. Admin-only.

    Query param:
      model_type — "b2b" (default) | "b2c"

    Returns:
      { auc, accuracy, samples, model_type, model_path, run_id }

    Raises 403 if caller does not have admin role.
    Raises 422 if insufficient feedback data to train.
    """
    from app.scoring.trainer import train_scoring_model, count_new_feedback
    from app.scoring.ml_scorer import clear_model_cache

    model_type = model_type.lower()
    if model_type not in ("b2b", "b2c"):
        raise HTTPException(
            status_code=422,
            detail="model_type must be 'b2b' or 'b2c'",
        )

    feedback_count = await count_new_feedback(db)
    logger.info(
        f"[retrain] Manual retrain triggered by admin — "
        f"model_type={model_type} feedback_count={feedback_count}"
    )

    result = await train_scoring_model(db=db, model_type=model_type)

    if result is None:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Insufficient training data for '{model_type}' model",
                "feedback_records": feedback_count,
                "minimum_required": 50,
            },
        )

    clear_model_cache()
    logger.info(
        f"[retrain] {model_type.upper()} model retrained by admin — "
        f"AUC={result['auc']:.3f} samples={result['samples']}"
    )
    return {
        "model_type": model_type,
        "auc":        round(result["auc"], 4),
        "accuracy":   round(result.get("accuracy", 0.0), 4),
        "samples":    result["samples"],
        "model_path": result["model_path"],
        "run_id":     result.get("run_id", ""),
        "message":    f"{model_type.upper()} model retrained successfully",
    }


@limiter.limit("2/hour")
@router.post(
    "/normalize",
    summary="Manually trigger Gemini bulk normalization (admin only)",
)
async def trigger_normalization(
    request: Request,
    background_tasks: BackgroundTasks,
    user: ZLUser = Depends(require_admin),
):
    """
    Fire the Gemini Flash-Lite bulk normalization job immediately as a background task.

    Useful for:
      - Testing normalization before the 3 AM scheduler fires.
      - Cleaning up a batch of freshly imported companies/people.

    The job runs asynchronously — the endpoint returns immediately with a
    status message. Check backend logs for progress and completion summary.

    Rate limited to 2 calls per hour per IP to prevent abuse.

    Returns:
        { status, message, job }
    """
    from app.jobs.normalizer_job import run_bulk_normalization

    logger.info(
        f"[normalize] Manual normalization triggered by user={user.id} "
        f"email={user.email}"
    )

    background_tasks.add_task(run_bulk_normalization)

    return {
        "status":  "started",
        "message": (
            "Bulk normalization is running in the background. "
            "Check backend logs for progress. "
            "The job normalizes industries, job titles, locations, and classifies insurance needs."
        ),
        "job": "bulk_normalizer",
    }


@limiter.limit("5/minute")
@router.post("/export/sheets")
async def export_sheets(
    request: Request,
    body: SheetsExportRequest,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Export leads to a new Google Sheet and return the shareable URL.

    If body.lead_ids is provided, exports only those leads (max 1000).
    Otherwise exports all of the user's leads sorted by score desc.

    The sheet is created via a service account and immediately shared
    (writer access) with the requesting user's email.
    """
    from datetime import date as _date

    from app.exports.sheets_client import export_leads_to_sheets

    # ── Load leads ────────────────────────────────────────────────────────────
    stmt = (
        select(ZLLead)
        .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
        .where(ZLLead.user_id == user.id)
        .order_by(ZLLead.lead_score.desc())
        .limit(1000)
    )
    if body.lead_ids:
        stmt = stmt.where(ZLLead.id.in_(body.lead_ids[:1000]))

    res     = await db.execute(stmt)
    leads   = res.scalars().unique().all()

    if not leads:
        raise HTTPException(status_code=404, detail="No leads found to export.")

    # ── Serialise to plain dicts (matches LeadResponse shape) ─────────────────
    lead_dicts = [LeadResponse.model_validate(l).model_dump() for l in leads]

    # ── Build sheet title ─────────────────────────────────────────────────────
    today = _date.today().isoformat()
    user_email = str(user.email) if user.email else "user"
    sheet_title = f"Zentro Leads — {user_email} — {today}"

    # ── Record export (pending) ───────────────────────────────────────────────
    export_record = ZLExport(
        user_id=user.id,
        export_type="google_sheets",
        lead_count=len(lead_dicts),
        status="pending",
        filters_used={"lead_ids": body.lead_ids} if body.lead_ids else {},
    )
    db.add(export_record)
    await db.flush()

    # ── Export to Google Sheets ───────────────────────────────────────────────
    try:
        sheets_url = await export_leads_to_sheets(
            leads=lead_dicts,
            sheet_title=sheet_title,
            user_email=user_email,
        )
    except ValueError as exc:
        # Service account not configured
        export_record.status = "failed"
        await db.commit()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        export_record.status = "failed"
        await db.commit()
        logger.error(f"Sheets export failed for user {user.id}: {exc}")
        raise HTTPException(status_code=500, detail="Google Sheets export failed — please try again.")

    # ── Mark complete ─────────────────────────────────────────────────────────
    export_record.sheets_url  = sheets_url
    export_record.status      = "completed"
    export_record.completed_at = datetime.now(UTC)
    await db.commit()

    logger.info(f"Sheets export: {len(lead_dicts)} leads → {sheets_url} for user {user.id}")
    return {"sheets_url": sheets_url, "lead_count": len(lead_dicts)}
