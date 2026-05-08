"""
Background job scheduler using APScheduler.
Runs 8 periodic jobs:
  1. Monthly lead limit reset
  2. Tender monitor (every 6h)
  3. Job board monitor (every 6h, offset 30min)
  4. SSM monitor (daily 6 AM)
  5. Renewal monitor (daily 7 AM)
  6. Daily digest (daily 7:30 AM)
  7. ML model retrain (weekly Sunday 2 AM)
  8. Bulk normalization via Gemini Flash-Lite (nightly 3 AM)
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
from app.jobs.normalizer_job import run_bulk_normalization

_scheduler: AsyncIOScheduler | None = None


async def _reset_monthly_lead_limits() -> None:
    """Reset leads_used_this_month to 0 for all users on the 1st of each month."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(ZLUser).values(leads_used_this_month=0)
        )
        await db.commit()
        logger.info(f"Reset monthly lead limits for {result.rowcount} users")


async def _retrain_models_job() -> None:
    """
    Retrain B2B and B2C XGBoost models if enough new feedback has accumulated.

    Runs weekly every Sunday at 2 AM.
    Skips silently if feedback count is below settings.MODEL_RETRAIN_THRESHOLD.
    After a successful retrain the in-process model cache is cleared so
    the next inference call loads the fresh model from disk.
    """
    from app.config import settings
    from app.scoring.trainer import count_new_feedback, train_scoring_model
    from app.scoring.ml_scorer import clear_model_cache

    logger.info("[scheduler] ML retrain job starting")
    try:
        async with AsyncSessionLocal() as db:
            feedback_count = await count_new_feedback(db)

        if feedback_count < settings.MODEL_RETRAIN_THRESHOLD:
            logger.info(
                f"[scheduler] Retrain skipped — only {feedback_count} feedback records "
                f"(threshold: {settings.MODEL_RETRAIN_THRESHOLD})"
            )
            return

        logger.info(
            f"[scheduler] {feedback_count} feedback records found — retraining models"
        )
        retrained: list[str] = []

        for model_type in ("b2b", "b2c"):
            async with AsyncSessionLocal() as db:
                result = await train_scoring_model(db, model_type)
            if result:
                retrained.append(
                    f"{model_type.upper()} AUC={result['auc']:.3f} "
                    f"samples={result['samples']}"
                )

        if retrained:
            clear_model_cache()
            logger.info(
                f"[scheduler] Models retrained and cache cleared: "
                + ", ".join(retrained)
            )
        else:
            logger.warning("[scheduler] Retrain ran but no models were produced")

    except Exception as exc:
        logger.error(f"[scheduler] ML retrain job failed: {exc}")


async def _bulk_normalization_job() -> None:
    """
    Nightly Gemini Flash-Lite bulk normalization.

    Normalizes industry labels, job titles, and location strings across
    all ZLCompany and ZLPerson records, then classifies insurance needs
    for B2B leads that have no insurance_type set.

    Runs nightly at 3:00 AM — after scrapers have completed their
    evening runs (tender/job-board at 6h intervals) and before the
    daily digest fires at 7:30 AM.
    """
    logger.info("[scheduler] Bulk normalization job starting")
    try:
        summary = await run_bulk_normalization()
        logger.info(
            "[scheduler] Bulk normalization complete — "
            + ", ".join(f"{k}={v}" for k, v in summary.items())
        )
    except Exception as exc:
        logger.error(f"[scheduler] Bulk normalization job failed: {exc}")


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

    # 7. ML Model Retrain — every Sunday at 2:00 AM
    _scheduler.add_job(
        _retrain_models_job,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="ml_retrain",
        replace_existing=True,
        max_instances=1,
    )

    # 8. Bulk Normalization (Gemini Flash-Lite) — nightly at 3:00 AM
    _scheduler.add_job(
        _bulk_normalization_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="bulk_normalizer",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        "APScheduler started with 8 jobs: "
        "monthly_reset, tender_monitor, job_board_monitor, "
        "ssm_monitor, renewal_monitor, daily_digest, ml_retrain, bulk_normalizer"
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("APScheduler shut down")
