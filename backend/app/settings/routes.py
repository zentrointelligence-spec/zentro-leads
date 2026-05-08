"""
Settings routes — integrations (ZIMS) config per user.

GET  /api/v1/settings/integrations       — fetch current ZIMS config
POST /api/v1/settings/integrations       — save ZIMS URL + API key
POST /api/v1/settings/integrations/test  — test-ping ZIMS health endpoint
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import get_current_user
from app.database import get_db
from app.models import ZLLead, ZLUser

router = APIRouter()


# ── Auth dependency wrapper (same pattern as all other routers) ───────────────

async def get_current_user_dep(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> ZLUser:
    """Dependency wrapper: injects db into get_current_user."""
    return await get_current_user(zentro_session=zentro_session, db=db)


# ── Schemas ──────────────────────────────────────────────────────────────────


class IntegrationsResponse(BaseModel):
    """Read-only view of the user's ZIMS integration config."""

    zims_linked: bool
    zims_api_url: Optional[str] = None
    zims_agency_id: Optional[str] = None
    zims_agent_id: Optional[str] = None
    zims_api_key_masked: Optional[str] = None
    zims_last_sync_at: Optional[datetime] = None
    zims_leads_pushed: int = 0
    leads_pushed_this_month: int = 0


class SaveIntegrationsRequest(BaseModel):
    """Payload to save ZIMS config."""

    zims_api_url: str
    zims_api_key: str
    zims_agency_id: Optional[str] = None
    zims_agent_id: Optional[str] = None


class TestConnectionResponse(BaseModel):
    """Result of the ZIMS connectivity test."""

    success: bool
    message: str
    zims_version: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mask_key(key: str | None) -> str | None:
    """Return a masked version of the API key for display (show last 6 chars)."""
    if not key or len(key) < 8:
        return None
    return f"{'•' * (len(key) - 6)}{key[-6:]}"


# ── Routes ───────────────────────────────────────────────────────────────────


@router.get(
    "/integrations",
    response_model=IntegrationsResponse,
    summary="Get ZIMS integration config",
)
async def get_integrations(
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> IntegrationsResponse:
    """Return the current user's ZIMS integration settings."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(ZLLead.id)).where(
            ZLLead.user_id == current_user.id,
            ZLLead.zims_pushed_at >= month_start,
        )
    )
    leads_this_month: int = result.scalar_one() or 0

    return IntegrationsResponse(
        zims_linked=bool(current_user.zims_linked),
        zims_api_url=str(current_user.zims_api_url) if current_user.zims_api_url else None,
        zims_agency_id=str(current_user.zims_agency_id) if current_user.zims_agency_id else None,
        zims_agent_id=str(current_user.zims_agent_id) if current_user.zims_agent_id else None,
        zims_api_key_masked=_mask_key(str(current_user.zims_api_key) if current_user.zims_api_key else None),
        zims_last_sync_at=current_user.zims_last_sync_at,  # type: ignore[arg-type]
        zims_leads_pushed=int(current_user.zims_leads_pushed or 0),
        leads_pushed_this_month=leads_this_month,
    )


@router.post(
    "/integrations",
    response_model=IntegrationsResponse,
    summary="Save ZIMS integration config",
)
async def save_integrations(
    payload: SaveIntegrationsRequest,
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> IntegrationsResponse:
    """Persist the ZIMS URL and API key for the current user."""
    url = payload.zims_api_url.rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ZIMS URL must start with http:// or https://",
        )
    if not payload.zims_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key cannot be empty",
        )
    zims_agency_id = (payload.zims_agency_id or "").strip()
    if zims_agency_id and not zims_agency_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ZIMS agency ID must be a number",
        )
    zims_agent_id = (payload.zims_agent_id or "").strip()

    current_user.zims_api_url = url  # type: ignore[assignment]
    current_user.zims_api_key = payload.zims_api_key.strip()  # type: ignore[assignment]
    current_user.zims_agency_id = zims_agency_id or None  # type: ignore[assignment]
    current_user.zims_agent_id = zims_agent_id or None  # type: ignore[assignment]
    current_user.zims_linked = True  # type: ignore[assignment]
    await db.commit()
    await db.refresh(current_user)

    logger.info(f"User {current_user.id} saved ZIMS config → {url}")
    return await get_integrations(current_user, db)


@router.post(
    "/integrations/test",
    response_model=TestConnectionResponse,
    summary="Test ZIMS connectivity",
)
async def test_integrations(
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> TestConnectionResponse:
    """
    Ping the ZIMS /health endpoint using the stored URL and API key.
    Returns success/failure with a human-readable message.
    """
    zims_url = str(current_user.zims_api_url) if current_user.zims_api_url else ""
    zims_key = str(current_user.zims_api_key) if current_user.zims_api_key else ""
    zims_agency_id = str(current_user.zims_agency_id) if current_user.zims_agency_id else ""
    zims_agent_id = str(current_user.zims_agent_id) if current_user.zims_agent_id else ""

    if not zims_url or not zims_key:
        return TestConnectionResponse(
            success=False,
            message="ZIMS URL and API key must be saved before testing.",
        )

    health_url = f"{zims_url.rstrip('/')}/health"
    validate_url = f"{zims_url.rstrip('/')}/api/v1/leads/import/validate"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                health_url,
                headers={"X-Internal-Key": zims_key},
            )
            validate_resp = await client.get(
                validate_url,
                headers={
                    "X-Internal-Key": zims_key,
                    "X-ZIMS-Agency-ID": zims_agency_id,
                    "X-ZIMS-Agent-ID": zims_agent_id,
                },
            )
        if resp.status_code in (200, 204) and validate_resp.status_code == 200:
            try:
                body = resp.json()
                version = body.get("version") or body.get("app_version")
            except Exception:
                version = None
            try:
                target = validate_resp.json()
                target_name = target.get("agency_name") or f"agency {zims_agency_id}"
            except Exception:
                target_name = f"agency {zims_agency_id}"
            return TestConnectionResponse(
                success=True,
                message=f"Connected to ZIMS successfully. Hot leads will route to {target_name}.",
                zims_version=version,
            )
        if validate_resp.status_code != 200:
            return TestConnectionResponse(
                success=False,
                message=f"ZIMS agency validation failed with HTTP {validate_resp.status_code}. Check the agency ID.",
            )
        return TestConnectionResponse(
            success=False,
            message=f"ZIMS returned HTTP {resp.status_code}. Check your API key.",
        )
    except httpx.ConnectError:
        return TestConnectionResponse(
            success=False,
            message="Cannot reach ZIMS — check the URL is correct and the server is running.",
        )
    except httpx.TimeoutException:
        return TestConnectionResponse(
            success=False,
            message="Connection to ZIMS timed out after 8 seconds.",
        )
    except Exception as exc:
        logger.warning(f"ZIMS test error for user {current_user.id}: {exc}")
        return TestConnectionResponse(
            success=False,
            message="Unexpected error while connecting to ZIMS.",
        )
