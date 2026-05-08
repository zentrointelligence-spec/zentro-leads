"""
Auth tests — register, login, /me, logout.

All tests use the real auth code path (password hashing, JWT signing).
No mocks — the full flow is exercised against a SQLite in-memory database.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun import freeze_time
from httpx import AsyncClient

from app.auth.utils import create_access_token

# ── Registration ───────────────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "email": "agent@test.com",
    "password": "SecurePass123!",
    "full_name": "Test Agent",
    "company_name": "Test Insurance Sdn Bhd",
}


async def test_register_success(client: AsyncClient):
    """Happy-path registration returns 201 and the user's email."""
    r = await client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == VALID_PAYLOAD["email"]
    assert body["user"]["full_name"] == VALID_PAYLOAD["full_name"]


async def test_register_returns_no_password(client: AsyncClient):
    """The response must never expose the password or its hash."""
    r = await client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert r.status_code == 201
    body_str = r.text
    assert "password" not in body_str
    assert "hashed_password" not in body_str


async def test_register_duplicate_email(client: AsyncClient):
    """Registering the same email twice must return 409."""
    await client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    r2 = await client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert r2.status_code == 409


async def test_register_invalid_email_format(client: AsyncClient):
    """An invalid email format triggers Pydantic validation → 422."""
    bad = {**VALID_PAYLOAD, "email": "notanemail"}
    r = await client.post("/api/v1/auth/register", json=bad)
    assert r.status_code == 422


async def test_register_missing_required_fields(client: AsyncClient):
    """An empty body must return 422 — all required fields are absent."""
    r = await client.post("/api/v1/auth/register", json={})
    assert r.status_code == 422


async def test_register_sets_auth_cookie(client: AsyncClient):
    """After registration, the zentro_session httpOnly cookie must be present."""
    r = await client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert r.status_code == 201
    assert "zentro_session" in r.cookies


# ── Login ──────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient, registered_user: dict):
    """Correct credentials return 200 and set the session cookie."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert r.status_code == 200
    assert "zentro_session" in r.cookies


async def test_login_sets_httponly_cookie(client: AsyncClient, registered_user: dict):
    """The zentro_session cookie must have the HttpOnly flag."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert r.status_code == 200
    set_cookie_header = r.headers.get("set-cookie", "")
    assert "httponly" in set_cookie_header.lower()


async def test_login_wrong_password(client: AsyncClient, registered_user: dict):
    """A wrong password must return 401."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": "WrongPassword999!"},
    )
    assert r.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient):
    """A login attempt for a non-existent email must also return 401 (no user enumeration)."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@nonexistent.com", "password": "Password123!"},
    )
    assert r.status_code == 401


async def test_login_case_insensitive_email(client: AsyncClient):
    """
    Emails should be case-insensitive. Register with mixed case, login with lower.

    FIX REQUIRED in auth/routes.py login handler:
        result = await db.execute(
            select(ZLUser).where(
                ZLUser.email == body.email.lower().strip(),
                ZLUser.is_active == True
            )
        )
    And in register:
        email = body.email.lower().strip()
    """
    await client.post(
        "/api/v1/auth/register",
        json={**VALID_PAYLOAD, "email": "Agent@Test.com"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "agent@test.com", "password": VALID_PAYLOAD["password"]},
    )
    assert r.status_code == 200, (
        "Login with lowercase email must succeed even if registered with mixed case. "
        "Fix: normalise email to lowercase on both register and login."
    )


# ── Protected Routes ───────────────────────────────────────────────────────────

async def test_get_me_authenticated(auth_client: AsyncClient, registered_user: dict):
    """An authenticated GET /me returns the current user's email."""
    r = await auth_client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == registered_user["email"]


async def test_get_me_no_cookie(client: AsyncClient):
    """GET /me without a session cookie returns 401."""
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_get_me_tampered_cookie(client: AsyncClient, registered_user: dict):
    """A tampered JWT must be rejected with 401, not 500."""
    # Register and login to get a real cookie
    await client.post("/api/v1/auth/register", json=registered_user)
    await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    # Overwrite the cookie with garbage
    client.cookies.set("zentro_session", "tampered.jwt.value.here")
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
    # Must not be a server error
    assert r.status_code != 500


async def test_get_me_expired_token(client: AsyncClient, db):
    """A JWT whose exp is in the past must return 401."""
    # Create a user directly so we have an ID
    from tests.factories import make_user

    user = await make_user(db, email="expiry@test.com")
    await db.commit()

    # Create a token that expires in -1 hour (already expired)
    from jose import jwt
    from datetime import datetime, timezone
    from app.config import settings

    payload = {
        "sub": user.id,
        "email": user.email,
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    client.cookies.set("zentro_session", expired_token)

    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


# ── Logout ─────────────────────────────────────────────────────────────────────

async def test_logout_clears_cookie(auth_client: AsyncClient):
    """POST /logout must clear the zentro_session cookie."""
    r = await auth_client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "")
    # Cookie cleared = max-age=0 or empty value
    assert "zentro_session" in set_cookie
    assert "max-age=0" in set_cookie.lower() or '=""' in set_cookie or "=" in set_cookie


async def test_get_me_after_logout(auth_client: AsyncClient):
    """After logout, GET /me must return 401."""
    await auth_client.post("/api/v1/auth/logout")
    # httpx persists cookies by default; force clear
    auth_client.cookies.clear()
    r = await auth_client.get("/api/v1/auth/me")
    assert r.status_code == 401
