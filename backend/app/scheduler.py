"""
Background job scheduler using APScheduler.
Runs 6 periodic jobs:
  1. Monthly lead limit reset
  2. Tender monitor (every 6h)
  3. Job board monitor (every 6h, offset 30min)
  4. SSM monitor (daily 6 AM)
  5. Renewal monitor (daily 7 AM)
  6. Daily digest (daily 7:30 AM)
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import update

from app.database import AsyncSessionLocal
from app.models import ZLUser
from app.jobs.tender_monitor import run_tender_monitor
from app.jobs.job_board_monitor import run_job_board_monitor
from app.jobs.daily_digest import run_daily_digest
from app.jobs.ssm_monitor import run_ssm_monitor
from app.jobs.renewal_monitor import run_renewal_monitor

_scheduler: AsyncIOScheduler | None = None


async def _reset_monthly_lead_limits() -> None:
    """Reset leads_used_this_month to 0 for all users on the 1st of each month."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(ZLUser).values(leads_used_this_month=0)
        )
        await db.commit()
        logger.info(f"Reset monthly lead limits for {result.rowcount} users")


def start_scheduler() -> AsyncIOScheduler:
    """Start the APScheduler with all periodic jobs."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler()

    # 1. Reset lead limits at 00:05 on the 1st of every month
    _scheduler.add_job(
        _reset_monthly_lead_limits,
        trigger=CronTrigger(day=1, hour=0, minute=5),
        id="reset_monthly_lead_limits",
        replace_existing=True,
    )

    # 2. Tender Monitor — every 6 hours
    _scheduler.add_job(
        run_tender_monitor,
        trigger=IntervalTrigger(hours=6),
        id="tender_monitor",
        replace_existing=True,
        max_instances=1,
    )

    # 3. Job Board Monitor — every 6 hours (offset by 30 min from tender)
    _scheduler.add_job(
        run_job_board_monitor,
        trigger=IntervalTrigger(hours=6, minutes=30),
        id="job_board_monitor",
        replace_existing=True,
        max_instances=1,
    )

    # 4. SSM Monitor — daily at 6:00 AM
    _scheduler.add_job(
        run_ssm_monitor,
        trigger=CronTrigger(hour=6, minute=0),
        id="ssm_monitor",
        replace_existing=True,
        max_instances=1,
    )

    # 5. Renewal Monitor — daily at 7:00 AM
    _scheduler.add_job(
        run_renewal_monitor,
        trigger=CronTrigger(hour=7, minute=0),
        id="renewal_monitor",
        replace_existing=True,
        max_instances=1,
    )

    # 6. Daily Digest — daily at 7:30 AM
    _scheduler.add_job(
        run_daily_digest,
        trigger=CronTrigger(hour=7, minute=30),
        id="daily_digest",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        "APScheduler started with 6 jobs: "
        "monthly_reset, tender_monitor, job_board_monitor, "
        "ssm_monitor, renewal_monitor, daily_digest"
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("APScheduler shut down")
