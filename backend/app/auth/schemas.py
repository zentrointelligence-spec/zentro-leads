"""Auth request and response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from typing import Optional
from app.models import PlanTier


class RegisterRequest(BaseModel):
    email:        EmailStr
    password:     str
    full_name:    str
    company_name: Optional[str] = None
    phone:        Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class UserResponse(BaseModel):
    id:                    str
    email:                 str
    full_name:             str
    company_name:          Optional[str] = None
    phone:                 Optional[str] = None
    avatar_url:            Optional[str] = None
    plan:                  PlanTier = PlanTier.FREE
    role:                  str = "agent"
    leads_used_this_month: int = 0
    leads_limit:           int = 25
    zims_linked:           bool = False

    model_config = ConfigDict(from_attributes=True)

    @field_validator("zims_linked", mode="before")
    @classmethod
    def default_zims_linked(cls, v: object) -> bool:
        """Coerce NULL (added by migration with no backfill) → False."""
        return bool(v) if v is not None else False

    @field_validator("leads_used_this_month", mode="before")
    @classmethod
    def default_leads_used(cls, v: object) -> int:
        """Coerce NULL → 0."""
        return int(v) if v is not None else 0

    @field_validator("leads_limit", mode="before")
    @classmethod
    def default_leads_limit(cls, v: object) -> int:
        """Coerce NULL → 25 (free-tier default)."""
        return int(v) if v is not None else 25

    @field_validator("plan", mode="before")
    @classmethod
    def default_plan(cls, v: object) -> PlanTier:
        """Coerce NULL → FREE."""
        if v is None:
            return PlanTier.FREE
        if isinstance(v, PlanTier):
            return v
        return PlanTier(v)

    @field_validator("role", mode="before")
    @classmethod
    def default_role(cls, v: object) -> str:
        if v is None or v == "":
            return "agent"
        return str(v)


class AuthResponse(BaseModel):
    message: str
    user:    UserResponse
