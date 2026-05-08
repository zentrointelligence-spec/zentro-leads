"""
Auth utilities — JWT creation, verification, password hashing,
cookie helpers. Matches ZIMS auth pattern exactly.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import warnings

from jose import JWTError, jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

with warnings.catch_warnings():
    # passlib.utils pulls in stdlib ``crypt`` even when only bcrypt is used; unused on 3.12+.
    warnings.simplefilter("ignore", DeprecationWarning)
    from passlib.context import CryptContext

from app.config import settings
from app.database import get_db
from app.models import ZLUser

# ── Password hashing ─────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────────────


def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        hours=settings.JWT_EXPIRY_HOURS
    )
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises HTTPException on failure."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
        )


def build_user_cookie_value(user: ZLUser) -> str:
    """Build the zentro_user cookie value (readable by JS)."""
    plan_value = user.plan.value if user.plan is not None else "free"
    return json.dumps({
        "id":           user.id,
        "email":        user.email,
        "full_name":    user.full_name or "",
        "company_name": user.company_name,
        "plan":         plan_value,
        "avatar_url":   user.avatar_url,
    })


# ── Current user dependency ───────────────────────────────────

async def get_current_user(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> ZLUser:
    """
    FastAPI dependency — reads zentro_session httpOnly cookie,
    decodes JWT, returns the authenticated ZLUser.
    """
    if not zentro_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    payload = decode_token(zentro_session)
    user_id: str = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    result = await db.execute(
        select(ZLUser).where(ZLUser.id == user_id, ZLUser.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    return user


# ── Role-gated dependencies ───────────────────────────────────

async def require_admin(
    current_user: ZLUser = Depends(get_current_user),
) -> ZLUser:
    """
    FastAPI dependency — only allows users with role='admin'.
    Raises HTTP 403 for any other authenticated role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


async def require_owner_or_admin(
    current_user: ZLUser = Depends(get_current_user),
) -> ZLUser:
    """
    FastAPI dependency — allows 'owner' or 'admin' roles.
    Raises HTTP 403 for plain 'agent' accounts.
    """
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency owner or admin access required.",
        )
    return current_user


async def require_any_auth(
    current_user: ZLUser = Depends(get_current_user),
) -> ZLUser:
    """
    FastAPI dependency — any authenticated user passes.
    Alias for clarity in route definitions where the intent is
    'this endpoint requires login but not a specific role'.
    """
    return current_user
