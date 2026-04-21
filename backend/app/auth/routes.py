"""
Auth routes — register, login, logout, /me
Sets httpOnly zentro_session + readable zentro_user cookies.
Matches ZIMS auth pattern exactly.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi import Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from loguru import logger
from typing import Optional

from app.database import get_db
from app.models import ZLUser, PlanTier
from app.auth.schemas import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from app.auth.utils import (
    hash_password, verify_password,
    create_access_token, build_user_cookie_value,
    get_current_user,
)

router = APIRouter()

# Plan limits map
PLAN_LIMITS = {
    PlanTier.FREE:    25,
    PlanTier.STARTER: 750,
    PlanTier.GROWTH:  3000,
    PlanTier.PRO:     10000,
    PlanTier.AGENCY:  999999,
}

COOKIE_OPTS = dict(
    httponly=False,
    samesite="lax",
    secure=False,   # True in production
    path="/",
)
SESSION_COOKIE_OPTS = dict(
    httponly=True,
    samesite="lax",
    secure=False,   # True in production
    path="/",
    max_age=86400,  # 24 hours
)


# ── POST /api/v1/auth/register ────────────────────────────────
@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new Zentro Leads account."""
    # Check duplicate email
    existing = await db.execute(
        select(ZLUser).where(ZLUser.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = ZLUser(
        email          = body.email,
        hashed_password= hash_password(body.password),
        full_name      = body.full_name,
        company_name   = body.company_name,
        phone          = body.phone,
        plan           = PlanTier.FREE,
        leads_limit    = PLAN_LIMITS[PlanTier.FREE],
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token(user.id, user.email)

    response.set_cookie("zentro_session", token, **SESSION_COOKIE_OPTS)
    response.set_cookie(
        "zentro_user", build_user_cookie_value(user), **COOKIE_OPTS
    )

    logger.info(f"New user registered: {user.email}")
    return AuthResponse(message="Account created successfully.", user=UserResponse.model_validate(user))


# ── POST /api/v1/auth/login ───────────────────────────────────
@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Login and receive session cookies."""
    result = await db.execute(
        select(ZLUser).where(ZLUser.email == body.email, ZLUser.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    token = create_access_token(user.id, user.email)

    response.set_cookie("zentro_session", token, **SESSION_COOKIE_OPTS)
    response.set_cookie(
        "zentro_user", build_user_cookie_value(user), **COOKIE_OPTS
    )

    logger.info(f"User logged in: {user.email}")
    return AuthResponse(message="Login successful.", user=UserResponse.model_validate(user))


# ── POST /api/v1/auth/logout ──────────────────────────────────
@router.post("/logout")
async def logout(response: Response):
    """Clear session cookies."""
    response.delete_cookie("zentro_session", path="/")
    response.delete_cookie("zentro_user",    path="/")
    return {"message": "Logged out successfully."}


# ── GET /api/v1/auth/me ───────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user."""
    user = await get_current_user(zentro_session=zentro_session, db=db)
    return UserResponse.model_validate(user)
