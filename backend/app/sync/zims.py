"""
ZIMS integration — push hot leads to companion product (non-blocking).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import ZLLead, ZLUser


async def push_lead_to_zims(lead_id: str) -> None:
    """
    Push a hot lead to ZIMS.

    Opens its own database session so it is safe to ``asyncio.create_task`` after
    the request-scoped session commits. Never raises — logs and returns on failure.
    """
    await asyncio.sleep(0.25)
    try:
        if not settings.ZIMS_API_URL or not settings.ZIMS_INTERNAL_API_KEY:
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ZLLead)
                .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
                .where(ZLLead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            if not lead:
                return

            user = await db.get(ZLUser, lead.user_id)
            if not user or not user.zims_linked:
                return

            payload = {
                "name": lead.person.full_name if lead.person else "Unknown",
                "email": lead.person.email if lead.person else None,
                "phone": lead.person.phone if lead.person else None,
                "company_name": lead.company.name if lead.company else None,
                "source": "zentro_leads",
                "lead_score": lead.lead_score,
                "intent_signals": lead.intent_signals or [],
            }

            base = settings.ZIMS_API_URL.rstrip("/")
            url = f"{base}/api/leads/import"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"X-Internal-Key": settings.ZIMS_INTERNAL_API_KEY},
                )

            if response.status_code in (200, 201):
                try:
                    body = response.json()
                except Exception:
                    body = {}
                lead.zims_lead_id = str(body.get("id") or body.get("lead_id") or "")
                lead.zims_pushed_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(f"Lead {lead_id} pushed to ZIMS")
            else:
                logger.warning(f"ZIMS push failed {response.status_code}: {response.text[:500]}")
    except Exception as exc:
        logger.warning(f"ZIMS push error (non-blocking): {exc}")
