"""
Admin API — full platform management for Zentro Intelligence staff.

Every endpoint requires role='admin' via the require_admin dependency.
A non-admin authenticated user gets HTTP 403. An unauthenticated request gets 401.

Prefix: /api/v1/admin
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import and_, case, desc, distinct, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    ActivityEvent,
    AgencyDetail,
    PlatformStats,
    QualityReport,
    ResetPasswordRequest,
    ServiceHealth,
    SystemHealth,
    UpdateUserRequest,
    UserListItem,
    UserListResponse,
)
from app.auth.utils import hash_password, require_admin
from app.database import get_db
from app.models import (
    ZLICP,
    ZLCompany,
    ZLLead,
    ZLLeadHistory,
    ZLPerson,
    ZLPipelineStage,
    ZLUser,
    LeadTier,
    PlanTier,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _today_utc() -> datetime:
    """Return the start of today in UTC (midnight)."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _week_start_utc() -> datetime:
    """Return the start of the current ISO week (Monday midnight UTC)."""
    today = _today_utc()
    return today - timedelta(days=today.weekday())


async def _get_user_or_404(user_id: str, db: AsyncSession) -> ZLUser:
    """Fetch a user by id, raise 404 if not found."""
    result = await db.execute(select(ZLUser).where(ZLUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


async def _build_user_list_item(user: ZLUser, db: AsyncSession) -> UserListItem:
    """Build a UserListItem for a single user, fetching counts."""
    lead_count_row = await db.execute(
        select(func.count()).where(ZLLead.user_id == user.id)
    )
    icp_count_row = await db.execute(
        select(func.count()).where(ZLICP.user_id == user.id, ZLICP.is_active == True)
    )
    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        role=user.role or "agent",
        plan=user.plan.value if user.plan else "free",
        is_active=bool(user.is_active),
        lead_count=lead_count_row.scalar() or 0,
        icp_count=icp_count_row.scalar() or 0,
        created_at=user.created_at,
        last_login=user.last_login_at,
    )


# ═══════════════════════════════════════════════════════════════
# Platform Overview
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Platform-wide aggregate statistics",
)
async def platform_stats(
    admin: ZLUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformStats:
    """
    Return real-time aggregate statistics for the whole platform.

    All counts are computed live from PostgreSQL — no caching here
    so the dashboard always reflects the current state.
    """
    today  = _today_utc()
    week   = _week_start_utc()

    # ── User counts ──────────────────────────────────────────────
    total_users = (await db.execute(select(func.count(ZLUser.id)))).scalar() or 0

    active_today = (await db.execute(
        select(func.count(ZLUser.id)).where(ZLUser.last_login_at >= today)
    )).scalar() or 0

    active_week = (await db.execute(
        select(func.count(ZLUser.id)).where(ZLUser.last_login_at >= week)
    )).scalar() or 0

    # ── Lead counts ──────────────────────────────────────────────
    total_leads = (await db.execute(select(func.count(ZLLead.id)))).scalar() or 0

    leads_today = (await db.execute(
        select(func.count(ZLLead.id)).where(ZLLead.created_at >= today)
    )).scalar() or 0

    leads_week = (await db.execute(
        select(func.count(ZLLead.id)).where(ZLLead.created_at >= week)
    )).scalar() or 0

    b2b_leads = (await db.execute(
        select(func.count(ZLLead.id)).where(ZLLead.lead_type == "b2b")
    )).scalar() or 0

    b2c_leads = (await db.execute(
        select(func.count(ZLLead.id)).where(ZLLead.lead_type == "b2c")
    )).scalar() or 0

    hot_leads = (await db.execute(
        select(func.count(ZLLead.id)).where(ZLLead.lead_score >= 85)
    )).scalar() or 0

    avg_score_row = (await db.execute(
        select(func.avg(ZLLead.lead_score))
    )).scalar()
    avg_score = float(avg_score_row) if avg_score_row is not None else 0.0

    # ── ICP & ZIMS counts ────────────────────────────────────────
    total_icps = (await db.execute(select(func.count(ZLICP.id)))).scalar() or 0

    total_zims = (await db.execute(
        select(func.count(ZLLead.id)).where(ZLLead.zims_pushed_at.isnot(None))
    )).scalar() or 0

    # ── Top industries (from zl_companies) ───────────────────────
    industry_rows = (await db.execute(
        select(ZLCompany.industry, func.count(ZLCompany.id).label("cnt"))
        .where(ZLCompany.industry.isnot(None))
        .group_by(ZLCompany.industry)
        .order_by(desc("cnt"))
        .limit(10)
    )).all()
    top_industries = [{"industry": r[0], "count": r[1]} for r in industry_rows]

    # ── Top locations (from zl_companies) ────────────────────────
    location_rows = (await db.execute(
        select(ZLCompany.city, func.count(ZLCompany.id).label("cnt"))
        .where(ZLCompany.city.isnot(None))
        .group_by(ZLCompany.city)
        .order_by(desc("cnt"))
        .limit(10)
    )).all()
    top_locations = [{"city": r[0], "count": r[1]} for r in location_rows]

    return PlatformStats(
        total_users=total_users,
        active_users_today=active_today,
        active_users_this_week=active_week,
        total_leads_generated=total_leads,
        leads_generated_today=leads_today,
        leads_generated_this_week=leads_week,
        total_b2b_leads=b2b_leads,
        total_b2c_leads=b2c_leads,
        hot_leads_total=hot_leads,
        average_lead_score=round(avg_score, 2),
        total_icps_created=total_icps,
        total_zims_pushes=total_zims,
        top_industries=top_industries,
        top_locations=top_locations,
        revenue_this_month=None,  # wired when Stripe revenue API is integrated
    )


@router.get(
    "/activity",
    response_model=list[ActivityEvent],
    summary="Last 50 significant platform events",
)
async def platform_activity(
    admin: ZLUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityEvent]:
    """
    Return the last 50 significant events across the platform.

    Sources:
    - zl_users: new registrations and plan upgrades
    - zl_lead_history: lead status changes and ZIMS pushes

    Events are merged and returned newest-first.
    """
    events: list[ActivityEvent] = []

    # ── New registrations (last 50) ──────────────────────────────
    reg_rows = (await db.execute(
        select(ZLUser.email, ZLUser.plan, ZLUser.created_at)
        .order_by(desc(ZLUser.created_at))
        .limit(50)
    )).all()

    for email, plan, ts in reg_rows:
        plan_str = plan.value if hasattr(plan, "value") else str(plan or "free")
        events.append(ActivityEvent(
            event_type="user_registered",
            user_email=email,
            detail=f"New user registered on '{plan_str}' plan",
            timestamp=ts,
        ))

    # ── Lead history events (last 50 zims_pushed + status changes) ──
    history_rows = (await db.execute(
        select(
            ZLLeadHistory.event_type,
            ZLLeadHistory.note,
            ZLLeadHistory.new_value,
            ZLLeadHistory.created_at,
            ZLUser.email,
        )
        .join(ZLLead, ZLLead.id == ZLLeadHistory.lead_id)
        .join(ZLUser, ZLUser.id == ZLLead.user_id, isouter=True)
        .where(ZLLeadHistory.event_type.in_(["zims_pushed", "status_change", "score_updated"]))
        .order_by(desc(ZLLeadHistory.created_at))
        .limit(50)
    )).all()

    for ev_type, note, new_val, ts, email in history_rows:
        detail = note or f"{ev_type} → {new_val or ''}"
        events.append(ActivityEvent(
            event_type=ev_type,
            user_email=email,
            detail=detail,
            timestamp=ts,
        ))

    # Sort combined list newest-first, return top 50
    events.sort(key=lambda e: e.timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return events[:50]


# ═══════════════════════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="Paginated list of all users with lead and ICP counts",
)
async def list_users(
    search:    Optional[str]  = Query(None, description="Search by email or company_name"),
    role:      Optional[str]  = Query(None),
    plan:      Optional[str]  = Query(None),
    is_active: Optional[bool] = Query(None),
    limit:     int            = Query(20, ge=1, le=200),
    offset:    int            = Query(0, ge=0),
    admin: ZLUser = Depends(require_admin),
    db:    AsyncSession = Depends(get_db),
) -> UserListResponse:
    """
    Return a paginated, filterable list of users.

    Counts for leads and ICPs are computed per-user via subqueries
    so the response includes full context for the admin dashboard.
    """
    # Lead count subquery
    lead_sq = (
        select(ZLLead.user_id, func.count(ZLLead.id).label("lead_count"))
        .group_by(ZLLead.user_id)
        .subquery()
    )
    # ICP count subquery (active only)
    icp_sq = (
        select(ZLICP.user_id, func.count(ZLICP.id).label("icp_count"))
        .where(ZLICP.is_active == True)
        .group_by(ZLICP.user_id)
        .subquery()
    )

    q = (
        select(
            ZLUser,
            func.coalesce(lead_sq.c.lead_count, 0).label("lead_count"),
            func.coalesce(icp_sq.c.icp_count, 0).label("icp_count"),
        )
        .outerjoin(lead_sq, lead_sq.c.user_id == ZLUser.id)
        .outerjoin(icp_sq,  icp_sq.c.user_id  == ZLUser.id)
    )

    if search:
        like = f"%{search}%"
        q = q.where(
            or_(ZLUser.email.ilike(like), ZLUser.company_name.ilike(like))
        )
    if role:
        q = q.where(ZLUser.role == role)
    if plan:
        try:
            plan_enum = PlanTier(plan.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid plan filter.",
            )
        q = q.where(ZLUser.plan == plan_enum)
    if is_active is not None:
        q = q.where(ZLUser.is_active == is_active)

    total_q  = select(func.count()).select_from(q.subquery())
    total    = (await db.execute(total_q)).scalar() or 0

    rows = (await db.execute(q.order_by(desc(ZLUser.created_at)).offset(offset).limit(limit))).all()

    items = []
    for row in rows:
        user, lead_count, icp_count = row.ZLUser, row.lead_count, row.icp_count
        items.append(UserListItem(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            role=user.role or "agent",
            plan=user.plan.value if user.plan else "free",
            is_active=bool(user.is_active),
            lead_count=lead_count,
            icp_count=icp_count,
            created_at=user.created_at,
            last_login=user.last_login_at,
        ))

    return UserListResponse(items=items, total=total)


@router.get(
    "/users/{user_id}",
    response_model=AgencyDetail,
    summary="Full profile of one agency",
)
async def get_user_detail(
    user_id: str,
    admin: ZLUser = Depends(require_admin),
    db:    AsyncSession = Depends(get_db),
) -> AgencyDetail:
    """
    Return the full agency profile: user record, last 10 leads,
    ICPs, pipeline stage counts, and last 20 activity events.
    """
    user = await _get_user_or_404(user_id, db)
    user_item = await _build_user_list_item(user, db)

    # ── Last 10 leads ────────────────────────────────────────────
    lead_rows = (await db.execute(
        select(ZLLead, ZLCompany.name, ZLPerson.full_name)
        .outerjoin(ZLCompany, ZLCompany.id == ZLLead.company_id)
        .outerjoin(ZLPerson,  ZLPerson.id  == ZLLead.person_id)
        .where(ZLLead.user_id == user_id)
        .order_by(desc(ZLLead.created_at))
        .limit(10)
    )).all()

    leads_out = []
    for row in lead_rows:
        lead, company_name, person_name = row
        leads_out.append({
            "id":           lead.id,
            "company_name": company_name or "",
            "person_name":  person_name  or "",
            "lead_score":   lead.lead_score,
            "lead_tier":    lead.lead_tier.value if lead.lead_tier else "cold",
            "status":       lead.status.value if lead.status else "new",
            "lead_type":    lead.lead_type,
            "created_at":   lead.created_at.isoformat() if lead.created_at else None,
        })

    # ── ICPs ─────────────────────────────────────────────────────
    icp_rows = (await db.execute(
        select(ZLICP)
        .where(ZLICP.user_id == user_id, ZLICP.is_active == True)
        .order_by(desc(ZLICP.created_at))
    )).scalars().all()

    icps_out = [
        {
            "id":         icp.id,
            "name":       icp.name,
            "industries": icp.industries,
            "locations":  icp.locations,
            "created_at": icp.created_at.isoformat() if icp.created_at else None,
        }
        for icp in icp_rows
    ]

    # ── Pipeline summary (count per stage) ───────────────────────
    stage_rows = (await db.execute(
        select(ZLPipelineStage.stage, func.count(ZLPipelineStage.id).label("cnt"))
        .where(ZLPipelineStage.user_id == user_id)
        .group_by(ZLPipelineStage.stage)
    )).all()

    pipeline_summary = {row[0]: row[1] for row in stage_rows}

    # ── Last 20 history events for this user's leads ─────────────
    activity_rows = (await db.execute(
        select(ZLLeadHistory)
        .join(ZLLead, ZLLead.id == ZLLeadHistory.lead_id)
        .where(ZLLead.user_id == user_id)
        .order_by(desc(ZLLeadHistory.created_at))
        .limit(20)
    )).scalars().all()

    recent_activity = [
        {
            "event_type": ev.event_type,
            "old_value":  ev.old_value,
            "new_value":  ev.new_value,
            "note":       ev.note,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in activity_rows
    ]

    return AgencyDetail(
        user=user_item,
        leads=leads_out,
        icps=icps_out,
        pipeline_summary=pipeline_summary,
        recent_activity=recent_activity,
    )


@router.patch(
    "/users/{user_id}",
    response_model=UserListItem,
    summary="Update a user's role, plan, or active status",
)
async def update_user(
    user_id: str,
    body:    UpdateUserRequest,
    admin:   ZLUser = Depends(require_admin),
    db:      AsyncSession = Depends(get_db),
) -> UserListItem:
    """
    Update role, plan, or is_active on a user account.

    - Deactivating a user (is_active=False) takes effect on their next API call.
    - Plan changes are recorded in plan_changed_at / plan_changed_by.
    """
    user = await _get_user_or_404(user_id, db)

    if body.role is not None:
        user.role = body.role

    if body.plan is not None:
        user.plan = PlanTier(body.plan)
        user.plan_changed_at = datetime.now(timezone.utc)
        user.plan_changed_by = admin.id
        logger.info(
            f"[admin] Plan changed: user={user_id} "
            f"new_plan={body.plan} by admin={admin.id}"
        )

    if body.is_active is not None:
        user.is_active = body.is_active
        if not body.is_active:
            logger.warning(
                f"[admin] User deactivated: user_id={user_id} by admin={admin.id}"
            )

    await db.commit()
    await db.refresh(user)
    return await _build_user_list_item(user, db)


@router.post(
    "/users/{user_id}/reset-password",
    summary="Reset a user's password (admin use for locked-out accounts)",
)
async def reset_password(
    user_id: str,
    body:    ResetPasswordRequest,
    admin:   ZLUser = Depends(require_admin),
    db:      AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """
    Hash and apply a new password for a user.

    Only intended for locked-out account recovery — not for routine resets.
    """
    user = await _get_user_or_404(user_id, db)
    user.hashed_password = hash_password(body.new_password)
    await db.commit()
    logger.warning(
        f"[admin] Password reset: user_id={user_id} by admin={admin.id}"
    )
    return {"success": True}


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Soft-delete a user account",
)
async def delete_user(
    user_id: str,
    admin:   ZLUser = Depends(require_admin),
    db:      AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-delete a user:
    - Sets is_active=False so all their API calls immediately return 401.
    - Appends _deleted_{timestamp} to the email so the slot is freed for
      re-registration without losing any lead / history data.

    Never performs a hard DELETE — all data is retained for compliance.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account.",
        )
    user = await _get_user_or_404(user_id, db)
    if not user.is_active and "_deleted_" in user.email:
        raise HTTPException(status_code=409, detail="User is already deleted.")

    ts = int(datetime.now(timezone.utc).timestamp())
    user.is_active = False
    user.email     = f"{user.email}_deleted_{ts}"
    await db.commit()
    logger.warning(
        f"[admin] User soft-deleted: user_id={user_id} by admin={admin.id}"
    )


# ═══════════════════════════════════════════════════════════════
# Lead Management
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/leads",
    summary="All leads across every agency (admin view)",
)
async def list_all_leads(
    user_id:   Optional[str]  = Query(None, description="Filter to one agency"),
    lead_type: Optional[str]  = Query(None),
    min_score: Optional[int]  = Query(None, ge=0, le=100),
    max_score: Optional[int]  = Query(None, ge=0, le=100),
    limit:     int            = Query(50, ge=1, le=500),
    offset:    int            = Query(0, ge=0),
    admin: ZLUser = Depends(require_admin),
    db:    AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return leads from all agencies.

    Supports the same filters as the agency lead endpoint plus an
    optional user_id to drill down to a single agency.
    """
    q = (
        select(ZLLead, ZLCompany.name, ZLPerson.full_name, ZLUser.email)
        .outerjoin(ZLCompany, ZLCompany.id == ZLLead.company_id)
        .outerjoin(ZLPerson,  ZLPerson.id  == ZLLead.person_id)
        .join(ZLUser,         ZLUser.id    == ZLLead.user_id)
    )

    if user_id:
        q = q.where(ZLLead.user_id == user_id)
    if lead_type:
        q = q.where(ZLLead.lead_type == lead_type)
    if min_score is not None:
        q = q.where(ZLLead.lead_score >= min_score)
    if max_score is not None:
        q = q.where(ZLLead.lead_score <= max_score)

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar() or 0

    rows = (await db.execute(
        q.order_by(desc(ZLLead.created_at)).offset(offset).limit(limit)
    )).all()

    items = []
    for row in rows:
        lead, company_name, person_name, user_email = row
        items.append({
            "id":           lead.id,
            "user_email":   user_email,
            "company_name": company_name or "",
            "person_name":  person_name  or "",
            "lead_score":   lead.lead_score,
            "lead_tier":    lead.lead_tier.value if lead.lead_tier else "cold",
            "lead_type":    lead.lead_type,
            "status":       lead.status.value if lead.status else "new",
            "source":       lead.source.value if lead.source else None,
            "market":       lead.market,
            "created_at":   lead.created_at.isoformat() if lead.created_at else None,
        })

    return {"items": items, "total": total}


@router.get(
    "/leads/quality-report",
    response_model=QualityReport,
    summary="Data quality metrics across all leads",
)
async def lead_quality_report(
    admin: ZLUser = Depends(require_admin),
    db:    AsyncSession = Depends(get_db),
) -> QualityReport:
    """
    Compute data quality metrics across the full lead corpus.

    Metrics include email verification rate, phone coverage,
    score distribution, average score by source, duplicate rate,
    and count of leads with no contact information.
    """
    total = (await db.execute(select(func.count(ZLLead.id)))).scalar() or 0

    if total == 0:
        return QualityReport(
            total_leads=0,
            email_verified_pct=0.0,
            phone_present_pct=0.0,
            score_distribution={"hot": 0, "warm": 0, "qualified": 0, "cold": 0},
            avg_score_by_source={},
            duplicate_rate=0.0,
            leads_without_contact=0,
        )

    # Email verified % (via zl_people join)
    verified = (await db.execute(
        select(func.count(ZLLead.id))
        .join(ZLPerson, ZLPerson.id == ZLLead.person_id, isouter=True)
        .where(ZLPerson.email_verified == True)
    )).scalar() or 0

    # Phone present % (via zl_people join)
    phone_present = (await db.execute(
        select(func.count(ZLLead.id))
        .join(ZLPerson, ZLPerson.id == ZLLead.person_id, isouter=True)
        .where(ZLPerson.phone.isnot(None))
    )).scalar() or 0

    # Score distribution
    hot_c  = (await db.execute(select(func.count(ZLLead.id)).where(ZLLead.lead_score >= 85))).scalar() or 0
    warm_c = (await db.execute(select(func.count(ZLLead.id)).where(and_(ZLLead.lead_score >= 60, ZLLead.lead_score < 85)))).scalar() or 0
    qual_c = (await db.execute(select(func.count(ZLLead.id)).where(and_(ZLLead.lead_score >= 40, ZLLead.lead_score < 60)))).scalar() or 0
    cold_c = (await db.execute(select(func.count(ZLLead.id)).where(ZLLead.lead_score < 40))).scalar() or 0

    # Avg score by source
    source_rows = (await db.execute(
        select(ZLLead.source, func.avg(ZLLead.lead_score).label("avg_score"))
        .where(ZLLead.source.isnot(None))
        .group_by(ZLLead.source)
    )).all()
    avg_by_source = {
        (r[0].value if hasattr(r[0], "value") else str(r[0])): round(float(r[1] or 0), 2)
        for r in source_rows
    }

    # Duplicate rate: people with more than one lead
    dup_row = (await db.execute(
        select(func.count())
        .select_from(
            select(ZLLead.person_id)
            .where(ZLLead.person_id.isnot(None))
            .group_by(ZLLead.person_id)
            .having(func.count(ZLLead.id) > 1)
            .subquery()
        )
    )).scalar() or 0
    duplicate_pct = round(100.0 * dup_row / total, 4) if total else 0.0

    # Leads without any contact info
    no_contact = (await db.execute(
        select(func.count(ZLLead.id))
        .join(ZLPerson, ZLPerson.id == ZLLead.person_id, isouter=True)
        .where(
            and_(
                or_(ZLPerson.email.is_(None), ZLPerson.email == ""),
                or_(ZLPerson.phone.is_(None), ZLPerson.phone == ""),
            )
        )
    )).scalar() or 0

    return QualityReport(
        total_leads=total,
        email_verified_pct=round(100.0 * verified / total, 2) if total else 0.0,
        phone_present_pct=round(100.0 * phone_present / total, 2) if total else 0.0,
        score_distribution={"hot": hot_c, "warm": warm_c, "qualified": qual_c, "cold": cold_c},
        avg_score_by_source=avg_by_source,
        duplicate_rate=duplicate_pct,
        leads_without_contact=no_contact,
    )


# ═══════════════════════════════════════════════════════════════
# System
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/system/health",
    response_model=SystemHealth,
    summary="Live health check of all platform services",
)
async def system_health(
    admin: ZLUser = Depends(require_admin),
    db:    AsyncSession = Depends(get_db),
) -> SystemHealth:
    """
    Perform live pings to every backing service and return latency + status.

    This endpoint never returns cached data — every call issues real probes.
    Latencies are measured in milliseconds.
    """

    # ── PostgreSQL ───────────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        await db.execute(text("SELECT 1"))
        pg_ms = round((time.perf_counter() - t0) * 1000, 2)
        pg_health = ServiceHealth(status="healthy", latency_ms=pg_ms)
    except Exception as exc:
        pg_health = ServiceHealth(status="down", detail=str(exc))

    # ── Redis ────────────────────────────────────────────────────
    try:
        from app.redis_client import get_redis
        r = get_redis()
        t0 = time.perf_counter()
        await r.ping()
        redis_ms = round((time.perf_counter() - t0) * 1000, 2)
        info = await r.info("memory")
        used_mb = round(info.get("used_memory", 0) / 1024 / 1024, 2)
        redis_health = ServiceHealth(
            status="healthy",
            latency_ms=redis_ms,
            detail=f"{used_mb} MB used",
        )
    except Exception as exc:
        redis_health = ServiceHealth(status="down", detail=str(exc))

    # ── Elasticsearch ────────────────────────────────────────────
    try:
        from app.search.elasticsearch_client import get_client as get_es
        es = get_es()
        t0 = time.perf_counter()
        info = await es.info()
        es_ms = round((time.perf_counter() - t0) * 1000, 2)
        # Count docs in leads index (best-effort)
        try:
            count_res = await es.count(index="zl_leads")
            es_detail = f"{count_res['count']} docs in zl_leads"
        except Exception:
            es_detail = "index count unavailable"
        es_health = ServiceHealth(status="healthy", latency_ms=es_ms, detail=es_detail)
    except Exception as exc:
        es_health = ServiceHealth(status="down", detail=str(exc))

    # ── Pinecone ─────────────────────────────────────────────────
    try:
        from app.search.pinecone_client import get_pinecone_index
        t0 = time.perf_counter()
        idx = await get_pinecone_index()
        pc_ms = round((time.perf_counter() - t0) * 1000, 2)
        if idx is not None:
            pc_health = ServiceHealth(status="healthy", latency_ms=pc_ms)
        else:
            pc_health = ServiceHealth(status="degraded", detail="Index not initialised")
    except Exception as exc:
        pc_health = ServiceHealth(status="down", detail=str(exc))

    # ── Anthropic ────────────────────────────────────────────────
    try:
        from app.icp.routes import anthropic_client
        # We don't make a live API call (costs money); confirm the client exists
        if anthropic_client is not None:
            ant_health = ServiceHealth(status="healthy", detail="Client initialised")
        else:
            ant_health = ServiceHealth(status="degraded", detail="Client not configured")
    except Exception as exc:
        ant_health = ServiceHealth(status="down", detail=str(exc))

    # ── Scheduler ────────────────────────────────────────────────
    try:
        from app.scheduler import _scheduler
        if _scheduler is not None and _scheduler.running:
            jobs = _scheduler.get_jobs()
            sched_health = ServiceHealth(
                status="healthy",
                detail=f"{len(jobs)} jobs scheduled",
            )
        else:
            sched_health = ServiceHealth(status="degraded", detail="Scheduler not running")
    except Exception as exc:
        sched_health = ServiceHealth(status="down", detail=str(exc))

    # ── Overall ──────────────────────────────────────────────────
    all_statuses = [
        pg_health.status, redis_health.status, es_health.status,
        pc_health.status, ant_health.status, sched_health.status,
    ]
    if "down" in all_statuses:
        overall = "down"
    elif "degraded" in all_statuses:
        overall = "degraded"
    else:
        overall = "ok"

    return SystemHealth(
        postgresql=pg_health,
        redis=redis_health,
        elasticsearch=es_health,
        pinecone=pc_health,
        anthropic=ant_health,
        scheduler=sched_health,
        overall=overall,
    )


@router.post(
    "/system/run-normalization",
    summary="Immediately trigger Gemini bulk normalization (admin only)",
)
async def run_normalization(
    background_tasks: BackgroundTasks,
    admin: ZLUser = Depends(require_admin),
) -> dict[str, str]:
    """
    Fire the Gemini Flash-Lite bulk normalization job as a background task.

    Returns immediately; check backend logs for progress.
    """
    from app.jobs.normalizer_job import run_bulk_normalization

    background_tasks.add_task(run_bulk_normalization)
    logger.info(f"[admin] Bulk normalization triggered by admin={admin.id}")
    return {"status": "started", "triggered_by": admin.email}


@router.post(
    "/system/retrain-models",
    summary="Immediately retrain B2B and B2C scoring models (admin only)",
)
async def retrain_models(
    background_tasks: BackgroundTasks,
    admin: ZLUser = Depends(require_admin),
) -> dict[str, str]:
    """
    Queue a full XGBoost retrain for both B2B and B2C models.

    Runs as a background task — returns immediately.
    New models take effect the moment training completes.
    """
    from app.database import AsyncSessionLocal
    from app.scoring.trainer import train_scoring_model
    from app.scoring.ml_scorer import clear_model_cache

    async def _retrain_both() -> None:
        """Train B2B then B2C; clear cache on success."""
        for model_type in ("b2b", "b2c"):
            try:
                async with AsyncSessionLocal() as db:
                    result = await train_scoring_model(db=db, model_type=model_type)
                if result:
                    logger.info(
                        f"[admin retrain] {model_type.upper()} done — "
                        f"AUC={result['auc']:.3f} samples={result['samples']}"
                    )
                else:
                    logger.warning(f"[admin retrain] {model_type.upper()} skipped — insufficient data")
            except Exception as exc:
                logger.error(f"[admin retrain] {model_type.upper()} failed: {exc}")
        clear_model_cache()

    background_tasks.add_task(_retrain_both)
    logger.info(f"[admin] Model retrain triggered by admin={admin.id}")
    return {"status": "started", "triggered_by": admin.email}
