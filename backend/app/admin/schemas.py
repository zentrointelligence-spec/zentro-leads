"""
Admin API — Pydantic schemas.
All schemas used by backend/app/admin/routes.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class UserListItem(BaseModel):
    """Summary row returned by GET /admin/users."""

    id:           str
    email:        str
    full_name:    str
    company_name: Optional[str] = None
    role:         str
    plan:         str
    is_active:    bool
    lead_count:   int
    icp_count:    int
    created_at:   datetime
    last_login:   Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("plan", mode="before")
    @classmethod
    def coerce_plan(cls, v: object) -> str:
        """Accept PlanTier enum or raw string."""
        if hasattr(v, "value"):
            return v.value
        return str(v) if v is not None else "free"

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role(cls, v: object) -> str:
        return str(v) if v is not None else "agent"


class UserListResponse(BaseModel):
    """Paginated list of users."""

    items: list[UserListItem]
    total: int


class UpdateUserRequest(BaseModel):
    """Fields an admin may update on a user account."""

    role:      Optional[str]  = None
    plan:      Optional[str]  = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("agent", "owner", "admin"):
            raise ValueError("role must be 'agent', 'owner', or 'admin'")
        return v

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: Optional[str]) -> Optional[str]:
        valid = {"free", "starter", "growth", "pro", "agency"}
        if v is not None and v not in valid:
            raise ValueError(f"plan must be one of {sorted(valid)}")
        return v


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class PlatformStats(BaseModel):
    """Aggregate platform-wide metrics."""

    total_users:              int
    active_users_today:       int
    active_users_this_week:   int
    total_leads_generated:    int
    leads_generated_today:    int
    leads_generated_this_week: int
    total_b2b_leads:          int
    total_b2c_leads:          int
    hot_leads_total:          int
    average_lead_score:       float
    total_icps_created:       int
    total_zims_pushes:        int
    top_industries:           list[dict[str, Any]]
    top_locations:            list[dict[str, Any]]
    revenue_this_month:       Optional[float] = None


class AgencyDetail(BaseModel):
    """Full profile of one agency returned by GET /admin/users/{id}."""

    user:             UserListItem
    leads:            list[dict[str, Any]]
    icps:             list[dict[str, Any]]
    pipeline_summary: dict[str, Any]
    recent_activity:  list[dict[str, Any]]


class ActivityEvent(BaseModel):
    """A single platform event for the activity feed."""

    event_type:  str
    user_email:  Optional[str] = None
    detail:      str
    timestamp:   Optional[datetime] = None


class QualityReport(BaseModel):
    """Lead data quality metrics."""

    total_leads:            int
    email_verified_pct:     float
    phone_present_pct:      float
    score_distribution:     dict[str, int]
    avg_score_by_source:    dict[str, float]
    duplicate_rate:         float
    leads_without_contact:  int


class ServiceHealth(BaseModel):
    """Health status of a single backing service."""

    status:      str   # "ok" | "degraded" | "down"
    latency_ms:  Optional[float] = None
    detail:      Optional[str]   = None


class SystemHealth(BaseModel):
    """Aggregated health of all platform services."""

    postgresql:          ServiceHealth
    redis:               ServiceHealth
    elasticsearch:       ServiceHealth
    pinecone:            ServiceHealth
    anthropic:           ServiceHealth
    scheduler:           ServiceHealth
    overall:             str  # "ok" | "degraded" | "down"
