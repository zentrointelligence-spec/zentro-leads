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

            # Prefer per-user config; fall back to global env config
            zims_url = str(user.zims_api_url) if user.zims_api_url else settings.ZIMS_API_URL
            zims_key = str(user.zims_api_key) if user.zims_api_key else settings.ZIMS_INTERNAL_API_KEY
            zims_agency_id = str(user.zims_agency_id) if user.zims_agency_id else ""
            zims_agent_id = str(user.zims_agent_id) if user.zims_agent_id else ""
            if not zims_url or not zims_key:
                return

            payload = {
                "name": lead.person.full_name if lead.person else "Unknown",
                "email": lead.person.email if lead.person else None,
                "phone": lead.person.phone if lead.person else None,
                "company_name": lead.company.name if lead.company else None,
                "source": "zentro_leads",
                "lead_score": lead.lead_score,
                "intent_signals": lead.intent_signals or [],
                "agent_id": zims_agent_id or None,
                "agent_email": str(user.email),
            }

            base = zims_url.rstrip("/")
            url = f"{base}/api/v1/leads/import"

            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"X-Internal-Key": zims_key}
                if zims_agency_id:
                    headers["X-ZIMS-Agency-ID"] = zims_agency_id
                if zims_agent_id:
                    headers["X-ZIMS-Agent-ID"] = zims_agent_id
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )

            if response.status_code in (200, 201):
                try:
                    body = response.json()
                except Exception:
                    body = {}
                lead.zims_lead_id = str(body.get("id") or body.get("lead_id") or "")
                lead.zims_pushed_at = datetime.now(timezone.utc)
                if user:
                    user.zims_last_sync_at = datetime.now(timezone.utc)
                    user.zims_leads_pushed = int(user.zims_leads_pushed or 0) + 1
                await db.commit()
                logger.info(f"Lead {lead_id} pushed to ZIMS")
            else:
                logger.warning(f"ZIMS push failed {response.status_code}: {response.text[:500]}")
    except Exception as exc:
        logger.warning(f"ZIMS push error (non-blocking): {exc}")
