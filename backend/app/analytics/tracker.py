"""
Conversion event tracker.
Records every funnel stage into zl_scoring_feedback for analytics + ML training.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ZLLead, ZLScoringFeedback


async def _already_tracked(
    db: AsyncSession,
    lead_id: str,
    event_type: str,
    user_id: str | None = None,
) -> bool:
    """Check if an event was already recorded for this lead to avoid duplicates."""
    stmt = select(ZLScoringFeedback).where(
        ZLScoringFeedback.lead_id == lead_id,
        ZLScoringFeedback.event_type == event_type,
    )
    if user_id:
        stmt = stmt.where(ZLScoringFeedback.user_id == user_id)
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


async def track_lead_generated(
    db: AsyncSession,
    lead: ZLLead,
) -> None:
    """
    Event 1: lead_generated
    Called once when a lead is created.
    """
    if await _already_tracked(db, str(lead.id), "lead_generated"):
        return

    feedback = ZLScoringFeedback(
        user_id=lead.user_id,
        lead_id=lead.id,
        icp_id=lead.icp_id,
        event_type="lead_generated",
        original_score=lead.lead_score,
        original_breakdown=lead.score_breakdown,
        intent_signals=lead.intent_signals,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(feedback)
    await db.flush()
    logger.info(f"Tracked lead_generated for lead {lead.id}")


async def track_lead_viewed(
    db: AsyncSession,
    lead_id: str,
    user_id: str,
) -> None:
    """
    Event 2: lead_viewed
    Called when a user opens a lead drawer/detail page.
    Deduped per user+lead.
    """
    if await _already_tracked(db, lead_id, "lead_viewed", user_id):
        return

    feedback = ZLScoringFeedback(
        user_id=user_id,
        lead_id=lead_id,
        event_type="lead_viewed",
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(feedback)
    await db.flush()
    logger.info(f"Tracked lead_viewed for lead {lead_id} by user {user_id}")


async def track_outreach_sent(
    db: AsyncSession,
    lead_id: str,
    user_id: str,
    channel: str,
) -> None:
    """
    Event 3: outreach_sent
    Called when a user copies/sends an outreach message.
    Channel: whatsapp | email | linkedin | sms
    """
    feedback = ZLScoringFeedback(
        user_id=user_id,
        lead_id=lead_id,
        event_type="outreach_sent",
        channel=channel,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(feedback)
    await db.flush()
    logger.info(f"Tracked outreach_sent ({channel}) for lead {lead_id}")


async def track_reply_received(
    db: AsyncSession,
    lead: ZLLead,
) -> None:
    """
    Event 4: reply_received
    Called when user marks lead status as 'replied'.
    Calculates days from lead creation to reply.
    """
    if await _already_tracked(db, str(lead.id), "reply_received"):
        return

    days_to_reply = 0
    if lead.created_at:
        delta = datetime.now(timezone.utc) - lead.created_at
        days_to_reply = max(0, delta.days)

    feedback = ZLScoringFeedback(
        user_id=lead.user_id,
        lead_id=lead.id,
        event_type="reply_received",
        days_to_reply=days_to_reply,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(feedback)
    await db.flush()
    logger.info(f"Tracked reply_received for lead {lead.id} ({days_to_reply} days)")


async def track_deal_closed(
    db: AsyncSession,
    lead: ZLLead,
    revenue_value: float | None = None,
) -> None:
    """
    Event 5: deal_closed
    Called when user marks lead status as 'won'.
    Also records the conversion for ML training.
    """
    if await _already_tracked(db, str(lead.id), "deal_closed"):
        return

    feedback = ZLScoringFeedback(
        user_id=lead.user_id,
        lead_id=lead.id,
        icp_id=lead.icp_id,
        event_type="deal_closed",
        original_score=lead.lead_score,
        original_breakdown=lead.score_breakdown,
        intent_signals=lead.intent_signals,
        converted=True,
        conversion_value=revenue_value,
        revenue_value=revenue_value,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(feedback)
    await db.flush()
    logger.info(f"Tracked deal_closed for lead {lead.id} (revenue: {revenue_value})")
