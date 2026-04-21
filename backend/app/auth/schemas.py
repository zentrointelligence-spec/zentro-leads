"""Auth request and response schemas."""

from pydantic import BaseModel, EmailStr, field_validator
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
    company_name:          Optional[str]
    phone:                 Optional[str]
    avatar_url:            Optional[str]
    plan:                  PlanTier
    leads_used_this_month: int
    leads_limit:           int
    zims_linked:           bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    message: str
    user:    UserResponse
