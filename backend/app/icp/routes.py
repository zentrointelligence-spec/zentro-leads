"""ICP routes — AI builder + CRUD."""

import hashlib
import json

import anthropic
from anthropic import AsyncAnthropic, APIError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from loguru import logger

from app.config import settings
from app.database import get_db
from app.models import ZLICP
from app.auth.utils import get_current_user
from app.redis_client import get_cached, set_cached, delete_cached, TTL_ICP
from app.icp.schemas import (
    ICPBuildRequest,
    ICPCreateRequest,
    ICPUpdateRequest,
    ICPResponse,
    ICPListResponse,
)

router = APIRouter()

CLAUDE_ICP_PROMPT = """You are an expert B2B sales strategist. A user sells the following: {description}
Return ONLY a JSON object (no markdown, no explanation) with these exact keys:
{{
  "suggested_name": "string (3-5 word ICP name)",
  "industries": ["string (5-8 best matching industries, e.g. 'Insurance', 'Financial Services', 'Real Estate')"],
  "job_titles": ["string (6-10 decision maker job titles, e.g. 'CEO', 'Managing Director', 'Operations Manager')"],
  "seniority_levels": ["string (from: c-level, director, manager, individual)"],
  "company_sizes": ["string (from: 1-10, 10-50, 50-200, 200-500, 500+)"],
  "locations": ["string (specific city names only, e.g. 'Kuala Lumpur', 'Singapore', 'Dubai')"],
  "keywords": ["string (8-12 relevant keywords)"],
  "intent_signals": ["string (from: hiring, funded, expanding, job_change, in_the_news, new_product)"],
  "search_queries": ["string (5-8 Google Maps business search queries — these MUST be short business category + city phrases that return real map listings, e.g. 'insurance agency Kuala Lumpur', 'insurance broker Singapore', 'financial advisor Penang'. DO NOT use generic web phrases like 'SME companies Malaysia' or 'fast growing startups'. Each query must be a real business type that appears on Google Maps.)"]
}}"""


def _icp_cache_key(user_id: str, description: str) -> str:
    digest = hashlib.sha256(description.encode()).hexdigest()[:16]
    return f"icp:{user_id}:{digest}"


async def _call_claude(description: str) -> dict:
    """Call Claude asynchronously to build ICP JSON from a business description."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY is not configured. Set it in backend/.env to use AI ICP building.",
        )
    try:
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": CLAUDE_ICP_PROMPT.format(description=description),
                }
            ],
        )
    except APIError as exc:
        logger.error(f"Anthropic API error during ICP build: {exc.status_code} {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {exc.message}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error calling Claude: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable. Please try again.",
        )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"Claude returned non-JSON ICP response: {exc} raw={raw[:300]!r}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unexpected format. Please try again.",
        )


# ── POST /api/v1/icp/build ────────────────────────────────────
@router.post("/build", response_model=ICPResponse, status_code=201)
async def build_icp_with_ai(
    body: ICPBuildRequest,
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Build an ICP from a one-sentence business description using Claude."""
    user = await get_current_user(zentro_session=zentro_session, db=db)

    cache_key = _icp_cache_key(user.id, body.description)
    cached = await get_cached(cache_key)
    if cached:
        logger.info(f"ICP cache hit for user {user.id}")
        # Fetch the saved record from DB instead of reconstructing from cache
        result = await db.execute(
            select(ZLICP).where(ZLICP.id == cached["id"])
        )
        icp = result.scalar_one_or_none()
        if icp:
            return ICPResponse.model_validate(icp)

    ai_data = await _call_claude(body.description)

    icp = ZLICP(
        user_id=user.id,
        name=ai_data.get("suggested_name", "My ICP"),
        description=body.description,
        industries=ai_data.get("industries", []),
        job_titles=ai_data.get("job_titles", []),
        seniority_levels=ai_data.get("seniority_levels", []),
        company_sizes=ai_data.get("company_sizes", []),
        locations=ai_data.get("locations", []),
        keywords=ai_data.get("keywords", []),
        intent_signals=ai_data.get("intent_signals", []),
        search_queries=ai_data.get("search_queries", []),
    )
    db.add(icp)
    await db.flush()
    await db.refresh(icp)

    await set_cached(cache_key, {"id": icp.id}, ttl=TTL_ICP)
    logger.info(f"ICP built and cached for user {user.id}: {icp.name}")
    return ICPResponse.model_validate(icp)


# ── POST /api/v1/icp/ ─────────────────────────────────────────
@router.post("/", response_model=ICPResponse, status_code=201)
async def create_icp(
    body: ICPCreateRequest,
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Create an ICP manually."""
    user = await get_current_user(zentro_session=zentro_session, db=db)

    icp = ZLICP(
        user_id=user.id,
        name=body.name,
        description=body.description,
        industries=body.industries,
        job_titles=body.job_titles,
        seniority_levels=body.seniority_levels,
        company_sizes=body.company_sizes,
        locations=body.locations,
        keywords=body.keywords,
        intent_signals=body.intent_signals,
        search_queries=body.search_queries,
    )
    db.add(icp)
    await db.flush()
    await db.refresh(icp)
    return ICPResponse.model_validate(icp)


# ── GET /api/v1/icp/ ──────────────────────────────────────────
@router.get("/", response_model=ICPListResponse)
async def list_icps(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List all active ICPs for the current user."""
    user = await get_current_user(zentro_session=zentro_session, db=db)
    result = await db.execute(
        select(ZLICP)
        .where(ZLICP.user_id == user.id, ZLICP.is_active == True)
        .order_by(ZLICP.created_at.desc())
    )
    icps = result.scalars().all()
    return ICPListResponse(
        items=[ICPResponse.model_validate(i) for i in icps],
        total=len(icps),
    )


# ── GET /api/v1/icp/{id} ──────────────────────────────────────
@router.get("/{icp_id}", response_model=ICPResponse)
async def get_icp(
    icp_id: str,
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get a single ICP by ID."""
    user = await get_current_user(zentro_session=zentro_session, db=db)
    result = await db.execute(
        select(ZLICP).where(ZLICP.id == icp_id, ZLICP.user_id == user.id)
    )
    icp = result.scalar_one_or_none()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found.")
    return ICPResponse.model_validate(icp)


# ── PATCH /api/v1/icp/{id} ────────────────────────────────────
@router.patch("/{icp_id}", response_model=ICPResponse)
async def update_icp(
    icp_id: str,
    body: ICPUpdateRequest,
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Update an ICP."""
    user = await get_current_user(zentro_session=zentro_session, db=db)
    result = await db.execute(
        select(ZLICP).where(ZLICP.id == icp_id, ZLICP.user_id == user.id)
    )
    icp = result.scalar_one_or_none()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found.")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(icp, field, value)

    await db.flush()
    await db.refresh(icp)

    await delete_cached(_icp_cache_key(user.id, icp.description or ""))
    return ICPResponse.model_validate(icp)


# ── DELETE /api/v1/icp/{id} ───────────────────────────────────
@router.delete("/{icp_id}", status_code=204)
async def delete_icp(
    icp_id: str,
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an ICP (sets is_active=False)."""
    user = await get_current_user(zentro_session=zentro_session, db=db)
    result = await db.execute(
        select(ZLICP).where(ZLICP.id == icp_id, ZLICP.user_id == user.id)
    )
    icp = result.scalar_one_or_none()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found.")

    icp.is_active = False
    await db.flush()
    await delete_cached(_icp_cache_key(user.id, icp.description or ""))
