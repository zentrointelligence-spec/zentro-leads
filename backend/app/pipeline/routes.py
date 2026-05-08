"""Pipeline CRM — stage management endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.utils import get_current_user
from app.database import get_db
from app.models import ZLCompany, ZLLead, ZLPerson, ZLPipelineStage, ZLUser
from app.pipeline.schemas import (
    PipelineEntryCreate,
    PipelineEntryMove,
    PipelineEntryResponse,
    PipelineListResponse,
)

router = APIRouter()

# ── Auth dependency ───────────────────────────────────────────────────────────


async def get_current_user_dep(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> ZLUser:
    """Dependency wrapper with DB injection."""
    return await get_current_user(zentro_session=zentro_session, db=db)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_entry_response(entry: ZLPipelineStage) -> PipelineEntryResponse:
    """
    Build a PipelineEntryResponse from a loaded ZLPipelineStage ORM object.

    Expects ``entry.lead``, ``entry.lead.person``, and ``entry.lead.company``
    to be already loaded (via selectinload).
    """
    lead: ZLLead = entry.lead
    person: ZLPerson | None = lead.person if lead else None
    company: ZLCompany | None = lead.company if lead else None

    name = (
        (person.full_name if person else None)
        or (company.name if company else None)
        or "Unknown"
    )
    email = person.email if person else None
    phone = person.phone if person else None
    tier = lead.lead_tier.value.upper() if lead and lead.lead_tier else None

    return PipelineEntryResponse(
        id=str(entry.id),
        stage=str(entry.stage),
        notes=str(entry.notes) if entry.notes else None,
        moved_at=entry.moved_at,  # type: ignore[arg-type]
        created_at=entry.created_at,  # type: ignore[arg-type]
        lead_id=str(entry.lead_id),
        name=name,
        company=company.name if company else None,
        email=str(email) if email else None,
        phone=str(phone) if phone else None,
        score=int(lead.lead_score) if lead and lead.lead_score is not None else None,
        tier=tier,
        product_type=str(lead.recommended_product) if lead and lead.recommended_product else None,
    )


async def _load_entry(
    entry_id: str,
    user_id: str,
    db: AsyncSession,
) -> ZLPipelineStage:
    """Load a pipeline entry by ID, scoped to the current user. Raises 404 if missing."""
    result = await db.execute(
        select(ZLPipelineStage)
        .where(
            ZLPipelineStage.id == entry_id,
            ZLPipelineStage.user_id == user_id,
        )
        .options(
            selectinload(ZLPipelineStage.lead).selectinload(ZLLead.person),
            selectinload(ZLPipelineStage.lead).selectinload(ZLLead.company),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found.")
    return entry


# ── GET /api/v1/pipeline/ ─────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=PipelineListResponse,
    summary="List all pipeline entries for the current user",
)
async def list_pipeline(
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> PipelineListResponse:
    """
    Return all CRM pipeline entries for the authenticated user, ordered by
    stage then creation date. Lead name, email, score and tier are included.
    """
    result = await db.execute(
        select(ZLPipelineStage)
        .where(ZLPipelineStage.user_id == current_user.id)
        .order_by(ZLPipelineStage.stage, ZLPipelineStage.created_at.desc())
        .options(
            selectinload(ZLPipelineStage.lead).selectinload(ZLLead.person),
            selectinload(ZLPipelineStage.lead).selectinload(ZLLead.company),
        )
    )
    entries = result.scalars().all()
    built = [_build_entry_response(e) for e in entries]
    return PipelineListResponse(entries=built, total=len(built))


# ── POST /api/v1/pipeline/ ────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=PipelineEntryResponse,
    status_code=201,
    summary="Add a lead to the pipeline",
)
async def add_to_pipeline(
    body: PipelineEntryCreate,
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> PipelineEntryResponse:
    """
    Add a lead to the user's pipeline. Idempotent — if the lead is already
    in the pipeline the existing entry is returned (HTTP 200 not 201).
    """
    # Verify the lead belongs to this user
    lead_result = await db.execute(
        select(ZLLead).where(
            ZLLead.id == body.lead_id,
            ZLLead.user_id == current_user.id,
        )
    )
    if not lead_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found.",
        )

    # Idempotency — return existing entry if already in pipeline
    existing_result = await db.execute(
        select(ZLPipelineStage)
        .where(
            ZLPipelineStage.user_id == current_user.id,
            ZLPipelineStage.lead_id == body.lead_id,
        )
        .options(
            selectinload(ZLPipelineStage.lead).selectinload(ZLLead.person),
            selectinload(ZLPipelineStage.lead).selectinload(ZLLead.company),
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        logger.debug(f"Lead {body.lead_id} already in pipeline for user {current_user.id}")
        return _build_entry_response(existing)

    entry = ZLPipelineStage(
        user_id=current_user.id,
        lead_id=body.lead_id,
        stage=body.stage,
        notes=body.notes,
    )
    db.add(entry)
    await db.flush()

    # Reload with relationships
    entry = await _load_entry(str(entry.id), str(current_user.id), db)
    await db.commit()

    logger.info(f"Pipeline: user {current_user.id} added lead {body.lead_id} → stage={body.stage}")
    return _build_entry_response(entry)


# ── PATCH /api/v1/pipeline/{id} ───────────────────────────────────────────────


@router.patch(
    "/{entry_id}",
    response_model=PipelineEntryResponse,
    summary="Move a pipeline entry to a different stage",
)
async def move_pipeline_entry(
    entry_id: str,
    body: PipelineEntryMove,
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> PipelineEntryResponse:
    """Update the stage (and optionally notes) of an existing pipeline entry."""
    entry = await _load_entry(entry_id, str(current_user.id), db)

    prev_stage = entry.stage
    entry.stage = body.stage  # type: ignore[assignment]
    if body.notes is not None:
        entry.notes = body.notes  # type: ignore[assignment]

    await db.commit()
    await db.refresh(entry)

    # Re-load with relationships after commit
    entry = await _load_entry(entry_id, str(current_user.id), db)

    logger.info(
        f"Pipeline: user {current_user.id} moved entry {entry_id} "
        f"{prev_stage} → {body.stage}"
    )
    return _build_entry_response(entry)


# ── DELETE /api/v1/pipeline/{id} ──────────────────────────────────────────────


@router.delete(
    "/{entry_id}",
    status_code=204,
    response_class=Response,
    summary="Remove a lead from the pipeline",
)
async def remove_from_pipeline(
    entry_id: str,
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a pipeline entry. The underlying lead is not deleted."""
    result = await db.execute(
        select(ZLPipelineStage).where(
            ZLPipelineStage.id == entry_id,
            ZLPipelineStage.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found.")

    await db.delete(entry)
    await db.commit()
    logger.info(f"Pipeline: user {current_user.id} removed entry {entry_id}")
    return Response(status_code=204)
