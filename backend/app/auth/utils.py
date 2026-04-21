"""
Auth utilities — JWT creation, verification, password hashing,
cookie helpers. Matches ZIMS auth pattern exactly.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import json

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Cookie, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models import ZLUser

# ── Password hashing ─────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    return json.dumps({
        "id":           user.id,
        "email":        user.email,
        "full_name":    user.full_name,
        "company_name": user.company_name,
        "plan":         user.plan.value,
        "avatar_url":   user.avatar_url,
    })


# ── Current user dependency ───────────────────────────────────

async def get_current_user(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = None,
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
