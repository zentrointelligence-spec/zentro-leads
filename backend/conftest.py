"""
Zentro Leads — Pytest conftest.

Architecture:
- Set critical env vars BEFORE any app import.
- Do NOT override POSTGRES_URL_ASYNC: database.py creates the engine at import
  time but never connects, so it works with the real PostgreSQL URL.
- Tests use their own function-scoped SQLite in-memory engine (complete isolation).
- ``get_db`` is overridden per-test to yield the SQLite session.
- External services (scheduler, ES, Pinecone, Redis) are mocked.
- Rate limiter is patched to use in-memory storage (no Redis needed).
"""

import os

# ── Must precede ALL app imports ───────────────────────────────────────────────
# Force DEBUG=false so Starlette's ServerErrorMiddleware returns 500 responses
# instead of re-raising exceptions (which would break integration tests).
os.environ["DEBUG"] = "false"
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-prod")
os.environ.setdefault("JWT_EXPIRY_HOURS", "24")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-dummy-for-ci")
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy-for-ci")
os.environ.setdefault("GOOGLE_GEMINI_API_KEY", "dummy-for-ci")
os.environ.setdefault("PINECONE_API_KEY", "")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("BILLPLZ_API_KEY", "dummy")
os.environ.setdefault("BILLPLZ_X_SIGNATURE", "test_x_sig_secret")
os.environ.setdefault("RAZORPAY_KEY_ID", "dummy")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test_razorpay_secret")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COOKIE_SAMESITE", "lax")
# NOTE: Do NOT override POSTGRES_URL_ASYNC here — database.py creates the engine
# at import time and SQLite doesn't support pool_size/max_overflow parameters.
# Tests override get_db with their own SQLite session; no PostgreSQL connection is made.

from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ZLICP, ZLCompany, ZLLead, ZLPerson, ZLPipelineStage, ZLUser  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ── Rate limiter: in-memory backend so Redis is not needed ────────────────────

@pytest.fixture(scope="session", autouse=True)
def patch_rate_limiter():
    """Swap slowapi's Redis storage for MemoryStorage for the full test session."""
    try:
        from limits.storage import MemoryStorage
        from app.rate_limiter import limiter
        original = limiter._storage
        limiter._storage = MemoryStorage()
        yield
        limiter._storage = original
    except Exception:
        yield


# ── Redis cache: no-op for all tests ──────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_redis_cache(monkeypatch):
    """
    Mock Redis cache operations globally.
    Tests that specifically verify cache behaviour override these locally.
    """
    monkeypatch.setattr("app.redis_client.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("app.redis_client.set_cached", AsyncMock(return_value=True))
    monkeypatch.setattr("app.redis_client.delete_cached", AsyncMock(return_value=True))
    monkeypatch.setattr("app.icp.routes.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("app.icp.routes.set_cached", AsyncMock(return_value=True))
    monkeypatch.setattr("app.icp.routes.delete_cached", AsyncMock(return_value=True))


# ── SQLite engine: fresh in-memory DB per test function ───────────────────────

@pytest.fixture
async def engine():
    """New SQLite in-memory engine for each test — maximum isolation, very fast."""
    _engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession backed by the test's SQLite engine."""
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        yield session


# ── FastAPI test client ────────────────────────────────────────────────────────

@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient wired to the app with:
      - DB dependency overridden to use the per-test SQLite session
      - Lifespan hooks (scheduler, Elasticsearch, Pinecone) mocked out
    """
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.scheduler.start_scheduler", return_value=None),
        patch("app.scheduler.shutdown_scheduler", return_value=None),
        patch("app.search.elasticsearch_client.ensure_leads_index", new=AsyncMock(return_value=None)),
        patch("app.search.elasticsearch_client.close_client", new=AsyncMock(return_value=None)),
        patch("app.search.pinecone_client.get_pinecone_index", new=AsyncMock(return_value=None)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Shared user fixtures ───────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "email": "agent@test.com",
    "password": "SecurePass123!",
    "full_name": "Test Agent",
    "company_name": "Test Insurance Sdn Bhd",
}


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Register a user via the API and return the payload used."""
    r = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 201, r.text
    return REGISTER_PAYLOAD


@pytest.fixture
async def auth_client(client: AsyncClient, registered_user: dict) -> AsyncClient:
    """Return the client after a successful login — session cookie is set."""
    r = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
async def auth_user_id(auth_client: AsyncClient) -> str:
    """Return the authenticated user's UUID from GET /auth/me."""
    r = await auth_client.get("/api/v1/auth/me")
    assert r.status_code == 200
    return r.json()["id"]
