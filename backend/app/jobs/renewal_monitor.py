"""
Renewal Monitor — Find leads due for insurance renewal.

Logic:
  - Leads created 10-11 months ago → policy likely expiring in 30-60 days
  - Companies with founded_year where 11 or 23 months have passed
    → anniversary renewal likely due

Updates flagged leads:
  - Add "renewal_due" to intent_signals
  - Boost score by 15 points
  - Update why_now with renewal message
  - Upgrade tier if score crosses thresholds
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import (
    LeadStatus,
    LeadTier,
    ZLAutoSignal,
    ZLCompany,
    ZLLead,
    ZLLeadHistory,
    ZLUser,
)


# ═══════════════════════════════════════════════════════════════
# Main Job
# ═══════════════════════════════════════════════════════════════


async def run_renewal_monitor() -> dict[str, Any]:
    """
    Renewal Monitor — daily at 7 AM.
    Flags leads approaching their policy renewal anniversary.
    """
    logger.info("Renewal Monitor: starting scan...")
    summary: dict[str, Any] = {
        "leads_checked": 0,
        "renewals_flagged": 0,
        "scores_boosted": 0,
        "signals_created": 0,
        "errors": 0,
    }

    now = datetime.now(timezone.utc)
    # 10-11 months ago window
    window_start = now - timedelta(days=340)
    window_end = now - timedelta(days=300)

    async with AsyncSessionLocal() as db:
        try:
            # ── Query 1: Leads created 10-11 months ago ──────────
            result = await db.execute(
                select(ZLLead)
                .where(
                    ZLLead.created_at >= window_start,
                    ZLLead.created_at <= window_end,
                    ZLLead.status.notin_([LeadStatus.CLOSED, LeadStatus.LOST, LeadStatus.SUPPRESSED]),
                )
                .options(selectinload(ZLLead.company), selectinload(ZLLead.person))
            )
            anniversary_leads = list(result.scalars().all())
            summary["leads_checked"] += len(anniversary_leads)

            for lead in anniversary_leads:
                try:
                    _flag_renewal(db, lead, now, summary)
                except Exception as exc:
                    logger.error(f"Renewal flag error for lead {lead.id}: {exc}")
                    summary["errors"] += 1
                    continue

            # ── Query 2: Companies with founded_year at 11 or 23 months ──
            current_year = now.year
            current_month = now.month

            result2 = await db.execute(
                select(ZLCompany).where(ZLCompany.founded_year.isnot(None))
            )
            companies = result2.scalars().all()

            for company in companies:
                if not company.founded_year:
                    continue
                try:
                    founded_month = 1  # Default to Jan if we only have year
                    founded_date = datetime(company.founded_year, founded_month, 1, tzinfo=timezone.utc)
                    age_months = (now.year - founded_date.year) * 12 + (now.month - founded_date.month)

                    if age_months in (11, 23, 35, 47):
                        # Find leads for this company
                        lead_result = await db.execute(
                            select(ZLLead)
                            .where(
                                ZLLead.company_id == company.id,
                                ZLLead.status.notin_([LeadStatus.CLOSED, LeadStatus.LOST, LeadStatus.SUPPRESSED]),
                            )
                            .options(selectinload(ZLLead.company))
                        )
                        for lead in lead_result.scalars().all():
                            _flag_renewal(db, lead, now, summary, source="company_anniversary")

                except Exception as exc:
                    logger.error(f"Renewal company {company.id} error: {exc}")
                    summary["errors"] += 1
                    continue

            await db.commit()

        except Exception as exc:
            await db.rollback()
            logger.exception(f"Renewal Monitor database error: {exc}")
            summary["errors"] += 1

    logger.info(
        f"Renewal Monitor: scan complete. "
        f"checked={summary['leads_checked']}, flagged={summary['renewals_flagged']}, "
        f"boosted={summary['scores_boosted']}, errors={summary['errors']}"
    )
    return summary


def _flag_renewal(
    db,
    lead: ZLLead,
    now: datetime,
    summary: dict[str, Any],
    source: str = "lead_anniversary",
) -> None:
    """Flag a single lead as renewal due."""
    signals = list(lead.intent_signals or [])
    if "renewal_due" in signals:
        return  # Already flagged

    old_score = lead.lead_score or 0
    new_score = min(100, old_score + 15)
    lead.lead_score = new_score

    if new_score >= 85:
        lead.lead_tier = LeadTier.HOT
    elif new_score >= 60:
        lead.lead_tier = LeadTier.WARM

    signals.append("renewal_due")
    lead.intent_signals = signals

    why_now = (
        f"\n\n[Renewal Monitor {now.strftime('%Y-%m-%d')}] "
        f"Policy renewal likely due — perfect time for competitive quote. "
        f"Company has had coverage for ~11 months."
    )
    lead.notes = (lead.notes or "") + why_now

    if not lead.recommended_product:
        lead.recommended_product = "Policy Renewal Review"

    db.add(
        ZLLeadHistory(
            lead_id=lead.id,
            event_type="signal_detected",
            old_value=str(old_score),
            new_value=str(new_score),
            note=f"Renewal flag: {source} (+15 score)",
            created_by="system",
        )
    )

    cname = lead.company.name if lead.company else "Unknown"
    signal = ZLAutoSignal(
        user_id=lead.user_id,
        company_id=lead.company_id,
        lead_id=lead.id,
        company_name=cname,
        signal_source="renewal_monitor",
        signal_type="renewal_due",
        signal_detail=f"Lead created ~11 months ago. {source}",
        why_now="Policy renewal likely due — perfect time for competitive quote",
        insurance_need="Policy Renewal Review",
        recommended_product="Policy Renewal Review",
        confidence=0.75,
    )
    db.add(signal)

    summary["renewals_flagged"] += 1
    summary["scores_boosted"] += 1
    summary["signals_created"] += 1

    logger.info(
        f"Renewal flagged: lead {lead.id} ({cname}) "
        f"score {old_score}→{new_score} via {source}"
    )
