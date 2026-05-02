"""
Analytics API routes — conversion funnel, event tracking endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import Cookie, APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.tracker import track_lead_viewed, track_outreach_sent
from app.auth.utils import get_current_user
from app.config import settings
from app.database import get_db
from app.leads.schemas import LeadStatusUpdate
from app.models import ZLLead, ZLScoringFeedback, ZLUser

router = APIRouter()


async def get_current_user_dep(
    zentro_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> ZLUser:
    return await get_current_user(zentro_session=zentro_session, db=db)


# ── POST track outreach sent ──────────────────────────────────
@router.post("/leads/{lead_id}/outreach")
async def record_outreach(
    lead_id: str,
    channel: str,  # whatsapp | email | linkedin | sms
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Record that outreach was sent/copied for a lead."""
    lead = await db.get(ZLLead, lead_id)
    if not lead or str(lead.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Lead not found.")

    if channel not in ("whatsapp", "email", "linkedin", "sms"):
        raise HTTPException(status_code=422, detail="Invalid channel.")

    await track_outreach_sent(db, lead_id, str(user.id), channel)
    return {"message": "Outreach recorded."}


# ── GET conversion funnel ─────────────────────────────────────
@router.get("/funnel")
async def conversion_funnel(
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return conversion funnel metrics for the current user.
    Stages: generated → viewed → contacted → replied → won
    """
    stages = [
        "lead_generated",
        "lead_viewed",
        "outreach_sent",
        "reply_received",
        "deal_closed",
    ]

    counts: dict[str, int] = {}
    for stage in stages:
        result = await db.execute(
            select(func.count())
            .select_from(ZLScoringFeedback)
            .where(
                ZLScoringFeedback.user_id == user.id,
                ZLScoringFeedback.event_type == stage,
            )
        )
        counts[stage] = int(result.scalar_one() or 0)

    # Calculate conversion rates between stages
    rates: dict[str, Any] = {}
    for i in range(1, len(stages)):
        prev = stages[i - 1]
        curr = stages[i]
        prev_count = counts.get(prev, 0)
        curr_count = counts.get(curr, 0)
        rate = round(100.0 * curr_count / prev_count, 2) if prev_count > 0 else 0.0
        rates[f"{prev}_to_{curr}"] = {
            "from_count": prev_count,
            "to_count": curr_count,
            "conversion_rate_pct": rate,
        }

    # Overall lead → won rate
    generated = counts.get("lead_generated", 0)
    won = counts.get("deal_closed", 0)
    overall_rate = round(100.0 * won / generated, 2) if generated > 0 else 0.0

    return {
        "counts": counts,
        "stage_conversions": rates,
        "overall_conversion_rate_pct": overall_rate,
        "total_leads": generated,
        "total_deals_won": won,
    }


# ── GET lead timeline ─────────────────────────────────────────
@router.get("/leads/{lead_id}/timeline")
async def lead_timeline(
    lead_id: str,
    user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all tracked events for a single lead."""
    lead = await db.get(ZLLead, lead_id)
    if not lead or str(lead.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Lead not found.")

    result = await db.execute(
        select(ZLScoringFeedback)
        .where(
            ZLScoringFeedback.lead_id == lead_id,
            ZLScoringFeedback.user_id == user.id,
        )
        .order_by(ZLScoringFeedback.recorded_at.asc())
    )
    events = result.scalars().all()

    return [
        {
            "event_type": e.event_type,
            "channel": e.channel,
            "days_to_reply": e.days_to_reply,
            "revenue_value": e.revenue_value,
            "score": e.original_score,
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
        }
        for e in events
    ]
