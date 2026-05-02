"""Pydantic v2 schemas for leads API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import LeadSource, LeadStatus, LeadTier


class PersonInLead(BaseModel):
    """Person nested inside a lead response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    job_title: str | None = None
    email: str | None = None
    email_verified: bool = False
    email_confidence: float = 0.0
    phone: str | None = None
    whatsapp: str | None = None
    linkedin_url: str | None = None


class CompanyInLead(BaseModel):
    """Company nested inside a lead response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    domain: str | None = None
    website: str | None = None
    industry: str | None = None
    employee_range: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    is_hiring: bool = False
    in_the_news: bool = False
    funding_stage: str | None = None
    google_rating: float | None = None
    years_in_business: str | None = None
    revenue_estimate: str | None = None
    is_malaysian_company: bool = False
    decision_maker_name: str | None = None
    decision_maker_title: str | None = None


class LeadResponse(BaseModel):
    """Single lead with nested person and company."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    lead_score: int
    lead_tier: LeadTier
    status: LeadStatus
    source: LeadSource | None = Field(default=None)
    intent_signals: list[Any] = Field(default_factory=list)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    ai_whatsapp_msg: str | None = None
    ai_email_subject: str | None = None
    ai_email_body: str | None = None
    ai_linkedin_note: str | None = None
    outreach_sent: bool = False
    notes: str | None = None
    follow_up_date: datetime | None = None
    zims_lead_id: str | None = None
    zims_pushed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    icp_match_score: int | None = None
    icp_verdict: str | None = None
    icp_reason: str | None = None
    recommended_product: str | None = None
    person: PersonInLead | None = None
    company: CompanyInLead | None = None


class LeadListResponse(BaseModel):
    """Paginated list of leads."""

    items: list[LeadResponse]
    total: int
    page: int
    per_page: int
    pages: int


class GenerateLeadsRequest(BaseModel):
    """Request body for async lead generation."""

    icp_id: str


class GenerateLeadsResponse(BaseModel):
    """Immediate acknowledgement for lead generation job."""

    message: str
    estimated_seconds: int
    icp_name: str


class LeadStatsResponse(BaseModel):
    """Aggregate counts for dashboard."""

    hot: int
    warm: int
    potential: int
    cold: int
    total: int
    used_this_month: int
    limit: int
    limit_percentage: float


class LeadStatusUpdate(BaseModel):
    """PATCH body for lead status."""

    status: LeadStatus


class LeadNoteUpdate(BaseModel):
    """PATCH body for lead notes."""

    note: str


class NLSearchRequest(BaseModel):
    """Natural-language search for leads."""

    query: str
