"""
Jobs API — Manual trigger endpoints for background monitors.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.utils import get_current_user
from app.database import get_db
from app.jobs.tender_monitor import run_tender_monitor
from app.jobs.job_board_monitor import run_job_board_monitor
from app.jobs.daily_digest import run_daily_digest
from app.jobs.ssm_monitor import run_ssm_monitor
from app.jobs.renewal_monitor import run_renewal_monitor
from app.models import ZLAutoSignal, ZLLead, ZLUser

router = APIRouter(prefix="/api/v1/jobs")


async def _get_admin_user(
    zentro_session: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> ZLUser:
    """Require authenticated user for manual triggers."""
    user = await get_current_user(zentro_session=zentro_session, db=db)
    return user


# ═══════════════════════════════════════════════════════════════
# Manual Triggers
# ═══════════════════════════════════════════════════════════════


@router.post("/tender/run")
async def trigger_tender_monitor(
    user: ZLUser = Depends(_get_admin_user),
) -> dict[str, Any]:
    """Manually run the tender monitor job."""
    logger.info(f"Manual trigger: tender_monitor by user {user.id}")
    result = await run_tender_monitor()
    return {"job": "tender_monitor", "result": result}


@router.post("/jobboard/run")
async def trigger_job_board_monitor(
    user: ZLUser = Depends(_get_admin_user),
) -> dict[str, Any]:
    """Manually run the job board monitor job."""
    logger.info(f"Manual trigger: job_board_monitor by user {user.id}")
    result = await run_job_board_monitor()
    return {"job": "job_board_monitor", "result": result}


@router.post("/ssm/run")
async def trigger_ssm_monitor(
    user: ZLUser = Depends(_get_admin_user),
) -> dict[str, Any]:
    """Manually run the SSM monitor job."""
    logger.info(f"Manual trigger: ssm_monitor by user {user.id}")
    result = await run_ssm_monitor()
    return {"job": "ssm_monitor", "result": result}


@router.post("/renewal/run")
async def trigger_renewal_monitor(
    user: ZLUser = Depends(_get_admin_user),
) -> dict[str, Any]:
    """Manually run the renewal monitor job."""
    logger.info(f"Manual trigger: renewal_monitor by user {user.id}")
    result = await run_renewal_monitor()
    return {"job": "renewal_monitor", "result": result}


@router.post("/digest/run")
async def trigger_daily_digest(
    user: ZLUser = Depends(_get_admin_user),
) -> dict[str, Any]:
    """Manually run the daily digest job."""
    logger.info(f"Manual trigger: daily_digest by user {user.id}")
    result = await run_daily_digest()
    return {"job": "daily_digest", "result": result}


# ═══════════════════════════════════════════════════════════════
# Job Status
# ═══════════════════════════════════════════════════════════════


@router.get("/status")
async def job_status() -> dict[str, Any]:
    """Return schedule and description for all background jobs."""
    return {
        "jobs": [
            {
                "name": "tender_monitor",
                "schedule": "every 6 hours",
                "description": "Monitors Malaysian business news RSS for tender wins and construction projects",
            },
            {
                "name": "job_board_monitor",
                "schedule": "every 6 hours (offset 30 min)",
                "description": "Scrapes job boards for hiring signals that indicate insurance needs",
            },
            {
                "name": "ssm_monitor",
                "schedule": "daily at 6:00 AM",
                "description": "Finds newly registered Malaysian companies via Google Search",
            },
            {
                "name": "renewal_monitor",
                "schedule": "daily at 7:00 AM",
                "description": "Flags leads approaching their policy renewal anniversary",
            },
            {
                "name": "daily_digest",
                "schedule": "daily at 7:30 AM",
                "description": "Sends WhatsApp + email digest with new HOT leads and top contacts",
            },
            {
                "name": "reset_monthly_lead_limits",
                "schedule": "1st of month at 00:05",
                "description": "Resets monthly lead generation counters for all users",
            },
        ]
    }


# ═══════════════════════════════════════════════════════════════
# Recent Signals Feed
# ═══════════════════════════════════════════════════════════════


@router.get("/signals/recent")
async def recent_signals(
    user: ZLUser = Depends(_get_admin_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Return recent auto-detected signals for the Live Signal Feed widget.
    """
    result = await db.execute(
        select(ZLAutoSignal)
        .where(ZLAutoSignal.user_id == user.id)
        .order_by(desc(ZLAutoSignal.detected_at))
        .limit(limit)
    )
    signals = result.scalars().all()

    out: list[dict[str, Any]] = []
    for sig in signals:
        out.append({
            "id": sig.id,
            "company_name": sig.company_name,
            "signal_source": sig.signal_source,
            "signal_type": sig.signal_type,
            "signal_detail": sig.signal_detail,
            "why_now": sig.why_now,
            "insurance_need": sig.insurance_need,
            "recommended_product": sig.recommended_product,
            "source_url": sig.source_url,
            "confidence": sig.confidence,
            "detected_at": sig.detected_at.isoformat() if sig.detected_at else None,
            "lead_id": sig.lead_id,
            "company_id": sig.company_id,
        })

    return out
