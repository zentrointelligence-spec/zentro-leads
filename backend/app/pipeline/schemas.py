"""Pydantic v2 schemas for the pipeline module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

# Valid stage values — keep in sync with frontend PipelineStage type
PipelineStageName = Literal[
    "new",
    "contacted",
    "qualified",
    "proposal",
    "closed_won",
    "closed_lost",
]


class PipelineEntryCreate(BaseModel):
    """Add a lead to the pipeline."""
    lead_id: str
    stage: PipelineStageName = "new"
    notes: Optional[str] = None


class PipelineEntryMove(BaseModel):
    """Move a pipeline entry to a new stage."""
    stage: PipelineStageName
    notes: Optional[str] = None


class PipelineLeadDetail(BaseModel):
    """Denormalised lead data embedded in every pipeline entry response."""
    lead_id: str
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    score: Optional[int] = None
    tier: Optional[str] = None
    product_type: Optional[str] = None


class PipelineEntryResponse(BaseModel):
    """Full pipeline entry returned by every endpoint."""
    id: str
    stage: str
    notes: Optional[str] = None
    moved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Lead data (flattened for frontend convenience)
    lead_id: str
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    score: Optional[int] = None
    tier: Optional[str] = None
    product_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PipelineListResponse(BaseModel):
    """Flat list of all pipeline entries for the current user."""
    entries: list[PipelineEntryResponse]
    total: int
