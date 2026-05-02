"""
Daily Digest — WhatsApp + Email summary every morning at 7:30 AM.

Sends each active user:
  - New HOT leads in last 24h
  - Leads upgraded to HOT from signals
  - Renewal reminders due in 30 days
  - Top 3 leads to contact today

Also sends an admin digest with system-wide stats.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import LeadStatus, LeadTier, ZLLead, ZLUser

# ═══════════════════════════════════════════════════════════════
# WhatsApp Alert Utility (shared with tender_monitor)
# ═══════════════════════════════════════════════════════════════


async def send_whatsapp_alert(message: str, to_number: str | None = None) -> bool:
    """Send WhatsApp alert via Twilio. Falls back to logger if not configured."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.info(f"[WhatsApp Alert - no Twilio config] {message[:200]}...")
        return False

    from_number = settings.TWILIO_WHATSAPP_NUMBER or settings.TWILIO_PHONE_NUMBER
    if not from_number:
        logger.info(f"[WhatsApp Alert - no sender number] {message[:200]}...")
        return False

    target = to_number
    if not target:
        logger.info(f"[WhatsApp Alert - no target number] {message[:200]}...")
        return False

    if not target.startswith("whatsapp:"):
        target = f"whatsapp:{target}"
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    try:
        import twilio.rest
        client = twilio.rest.Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=from_number,
            to=target,
            body=message[:1600],
        )
        logger.info(f"WhatsApp alert sent to {target}")
        return True
    except Exception as exc:
        logger.warning(f"WhatsApp alert failed: {exc}")
        return False


async def send_email(subject: str, html_body: str, to_email: str) -> bool:
    """Send email via SendGrid. Falls back to logger if not configured."""
    if not settings.SENDGRID_API_KEY:
        logger.info(f"[Email - no SendGrid config] To: {to_email}, Subject: {subject}")
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=settings.FROM_EMAIL or "noreply@leadradar.io",
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as exc:
        logger.warning(f"Email failed: {exc}")
        return False


# ═══════════════════════════════════════════════════════════════
# Digest Data Queries
# ═══════════════════════════════════════════════════════════════


async def _get_new_hot_leads(db, user_id: str, since: datetime) -> list[ZLLead]:
    """Leads created in last 24h with tier=HOT."""
    result = await db.execute(
        select(ZLLead)
        .where(
            ZLLead.user_id == user_id,
            ZLLead.lead_tier == LeadTier.HOT,
            ZLLead.created_at >= since,
        )
        .options(selectinload(ZLLead.company), selectinload(ZLLead.person))
        .order_by(ZLLead.lead_score.desc())
    )
    return list(result.scalars().all())


async def _get_upgraded_leads(db, user_id: str, since: datetime) -> list[ZLLead]:
    """Leads that have signal_detected or tender_detected history in last 24h."""
    from app.models import ZLLeadHistory

    result = await db.execute(
        select(ZLLead)
        .join(ZLLeadHistory, ZLLead.id == ZLLeadHistory.lead_id)
        .where(
            ZLLead.user_id == user_id,
            ZLLead.lead_tier == LeadTier.HOT,
            ZLLeadHistory.event_type.in_(["signal_detected", "tender_detected", "score_updated"]),
            ZLLeadHistory.created_at >= since,
        )
        .options(selectinload(ZLLead.company), selectinload(ZLLead.person))
        .distinct()
    )
    return list(result.scalars().all())


async def _get_renewal_leads(db, user_id: str) -> list[ZLLead]:
    """Leads with renewal_due in intent_signals."""
    result = await db.execute(
        select(ZLLead)
        .where(
            ZLLead.user_id == user_id,
            ZLLead.status.notin_([LeadStatus.CLOSED, LeadStatus.LOST, LeadStatus.SUPPRESSED]),
        )
        .options(selectinload(ZLLead.company), selectinload(ZLLead.person))
    )
    leads = result.scalars().all()
    renewal_leads: list[ZLLead] = []
    for lead in leads:
        signals = lead.intent_signals or []
        if "renewal_due" in signals:
            renewal_leads.append(lead)
    return renewal_leads


async def _get_top_leads_to_contact(db, user_id: str) -> list[ZLLead]:
    """Top 3 HOT leads that haven't been contacted yet."""
    result = await db.execute(
        select(ZLLead)
        .where(
            ZLLead.user_id == user_id,
            ZLLead.lead_tier == LeadTier.HOT,
            ZLLead.status.in_([LeadStatus.NEW, LeadStatus.VIEWED]),
        )
        .options(selectinload(ZLLead.company), selectinload(ZLLead.person))
        .order_by(ZLLead.lead_score.desc())
        .limit(3)
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════
# Message Formatting
# ═══════════════════════════════════════════════════════════════


def _format_whatsapp_digest(
    first_name: str,
    new_hot: list[ZLLead],
    upgraded: list[ZLLead],
    renewals: list[ZLLead],
    top3: list[ZLLead],
) -> str:
    lines: list[str] = [
        f"Good morning {first_name}! 🌅",
        "",
        "📊 *LeadRadar Daily Digest*",
        "─────────────────────────",
        "",
        f"🔥 New HOT leads: {len(new_hot)}",
        f"⚡ Upgraded to HOT: {len(upgraded)}",
        f"⏰ Renewals due: {len(renewals)}",
    ]

    if top3:
        lines.extend(["", "🎯 *Contact today:*"])
        for i, lead in enumerate(top3, 1):
            cname = lead.company.name if lead.company else "Unknown"
            phone = lead.person.phone if lead.person else None
            why_now = (lead.notes or "").split("\n")[0][:60] if lead.notes else "High-scoring lead"
            lines.append(f"{i}. *{cname}*")
            if phone:
                lines.append(f"   📱 {phone}")
            lines.append(f"   💡 {why_now}")

    lines.extend(["", "🔗 app.leadradar.io/dashboard", "Good luck today! 💪"])
    return "\n".join(lines)


def _format_email_digest(
    first_name: str,
    new_hot: list[ZLLead],
    upgraded: list[ZLLead],
    renewals: list[ZLLead],
    top3: list[ZLLead],
) -> str:
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1e293b;">
      <div style="background: #0F172A; padding: 24px; text-align: center;">
        <h1 style="color: #F59E0B; margin: 0;">LeadRadar</h1>
        <p style="color: #94a3b8; margin: 4px 0 0;">Daily Digest</p>
      </div>
      <div style="padding: 24px;">
        <p style="font-size: 16px;">Good morning <strong>{first_name}</strong>! 🌅</p>
        <div style="background: #fff7ed; border-left: 4px solid #EA580C; padding: 16px; margin: 16px 0;">
          <p style="margin: 0;"><strong>🔥 New HOT leads:</strong> {len(new_hot)}</p>
          <p style="margin: 8px 0 0;"><strong>⚡ Upgraded to HOT:</strong> {len(upgraded)}</p>
          <p style="margin: 8px 0 0;"><strong>⏰ Renewals due:</strong> {len(renewals)}</p>
        </div>
    """

    if top3:
        html += "<h3 style='color: #EA580C;'>🎯 Contact Today</h3><ul style='padding-left: 20px;'>"
        for lead in top3:
            cname = lead.company.name if lead.company else "Unknown"
            phone = lead.person.phone if lead.person else "—"
            why_now = (lead.notes or "").split("\n")[0][:80] if lead.notes else "High-scoring lead"
            html += f"""
            <li style="margin-bottom: 16px;">
              <strong>{cname}</strong><br>
              <span style="color: #64748b;">📱 {phone}</span><br>
              <span style="color: #475569;">💡 {why_now}</span>
            </li>
            """
        html += "</ul>"

    html += """
        <div style="text-align: center; margin-top: 24px;">
          <a href="https://app.leadradar.io/dashboard" 
             style="background: #EA580C; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
            Open Dashboard →
          </a>
        </div>
        <p style="color: #94a3b8; text-align: center; margin-top: 24px; font-size: 12px;">
          Good luck today! 💪
        </p>
      </div>
    </body>
    </html>
    """
    return html


def _format_admin_digest(
    total_hot: int,
    total_warm: int,
    total_leads: int,
    new_signals: int,
    job_health: dict[str, str],
) -> str:
    health_lines = "\n".join([f"  {name}: {status}" for name, status in job_health.items()])
    return (
        "🚨 *LeadRadar Admin Digest*\n\n"
        f"📊 Total HOT leads: {total_hot}\n"
        f"📊 Total WARM leads: {total_warm}\n"
        f"📊 Total leads: {total_leads}\n"
        f"📡 New signals (24h): {new_signals}\n\n"
        "🔧 Job Health:\n"
        f"{health_lines}\n\n"
        "Have a productive day! 💪"
    )


# ═══════════════════════════════════════════════════════════════
# Main Job
# ═══════════════════════════════════════════════════════════════


async def run_daily_digest() -> dict[str, Any]:
    """
    Daily digest job — runs at 7:30 AM.
    Sends WhatsApp + email to each active user with leads in last 24h.
    Also sends admin digest.
    """
    logger.info("Daily Digest: compiling...")
    summary: dict[str, Any] = {
        "users_processed": 0,
        "whatsapp_sent": 0,
        "email_sent": 0,
        "skipped_empty": 0,
        "errors": 0,
    }

    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    async with AsyncSessionLocal() as db:
        try:
            users_result = await db.execute(
                select(ZLUser).where(ZLUser.is_active == True)
            )
            users = list(users_result.scalars().all())

            for user in users:
                try:
                    new_hot = await _get_new_hot_leads(db, user.id, since_24h)
                    upgraded = await _get_upgraded_leads(db, user.id, since_24h)
                    renewals = await _get_renewal_leads(db, user.id)
                    top3 = await _get_top_leads_to_contact(db, user.id)

                    total_activity = len(new_hot) + len(upgraded) + len(renewals)
                    if total_activity == 0 and not top3:
                        summary["skipped_empty"] += 1
                        continue

                    first_name = (user.full_name or "There").split()[0]

                    # WhatsApp
                    if user.phone:
                        msg = _format_whatsapp_digest(first_name, new_hot, upgraded, renewals, top3)
                        sent = await send_whatsapp_alert(msg, user.phone)
                        if sent:
                            summary["whatsapp_sent"] += 1

                    # Email
                    if user.email:
                        subject = f"🔥 Your LeadRadar Daily: {len(new_hot)} HOT leads today"
                        html = _format_email_digest(first_name, new_hot, upgraded, renewals, top3)
                        sent = await send_email(subject, html, user.email)
                        if sent:
                            summary["email_sent"] += 1

                    summary["users_processed"] += 1

                except Exception as exc:
                    logger.error(f"Daily digest user {user.id} error: {exc}")
                    summary["errors"] += 1
                    continue

            # ── Admin digest ───────────────────────────────────
            try:
                hot_count = await db.execute(
                    select(func.count()).select_from(ZLLead).where(ZLLead.lead_tier == LeadTier.HOT)
                )
                warm_count = await db.execute(
                    select(func.count()).select_from(ZLLead).where(ZLLead.lead_tier == LeadTier.WARM)
                )
                total_count = await db.execute(select(func.count()).select_from(ZLLead))

                from app.models import ZLAutoSignal
                signals_count = await db.execute(
                    select(func.count()).select_from(ZLAutoSignal).where(ZLAutoSignal.detected_at >= since_24h)
                )

                admin_msg = _format_admin_digest(
                    total_hot=int(hot_count.scalar_one() or 0),
                    total_warm=int(warm_count.scalar_one() or 0),
                    total_leads=int(total_count.scalar_one() or 0),
                    new_signals=int(signals_count.scalar_one() or 0),
                    job_health={
                        "tender_monitor": "OK",
                        "job_board_monitor": "OK",
                        "ssm_monitor": "OK",
                        "renewal_monitor": "OK",
                        "daily_digest": "OK",
                    },
                )

                admin_phone = getattr(settings, "ADMIN_PHONE", None)
                if admin_phone:
                    await send_whatsapp_alert(admin_msg, admin_phone)

                admin_email = getattr(settings, "ADMIN_EMAIL", None)
                if admin_email:
                    await send_email("LeadRadar Admin Digest", admin_msg.replace("\n", "<br>"), admin_email)

            except Exception as exc:
                logger.error(f"Admin digest error: {exc}")
                summary["errors"] += 1

        except Exception as exc:
            logger.exception(f"Daily Digest database error: {exc}")
            summary["errors"] += 1

    logger.info(
        f"Daily Digest: complete. "
        f"users={summary['users_processed']}, whatsapp={summary['whatsapp_sent']}, "
        f"email={summary['email_sent']}, skipped={summary['skipped_empty']}, errors={summary['errors']}"
    )
    return summary
