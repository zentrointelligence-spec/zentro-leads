"""
Leads API tests.

All external services (Elasticsearch, Pinecone, ZIMS sync) are mocked via
autouse fixtures. The tests talk to the FastAPI app through the ASGI transport
against a fresh SQLite in-memory database.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LeadStatus
from tests.factories import make_company, make_lead, make_person, make_user


# ── Autouse: kill all external I/O ────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """
    Prevent any real network calls during lead tests.
    These patches target the modules that leads/routes.py actually imports.
    """
    monkeypatch.setattr(
        "app.search.elasticsearch_client.index_lead", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.search.pinecone_client.upsert_lead_embedding", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.sync.zims.push_lead_to_zims", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.analytics.tracker.track_lead_viewed", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.analytics.tracker.track_reply_received", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.analytics.tracker.track_deal_closed", AsyncMock(return_value=None)
    )


# ── List Leads ─────────────────────────────────────────────────────────────────

async def test_list_leads_empty(auth_client: AsyncClient):
    """A fresh account has no leads → empty paginated response."""
    r = await auth_client.get("/api/v1/leads/")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_leads_returns_only_own_leads(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """
    User A has 3 leads, User B has 2 leads.
    User A's GET /leads/ must return exactly 3 items (not 5).
    """
    user_b = await make_user(db, email="userb@leads.test")
    # 3 leads for user A
    for i in range(3):
        await make_lead(db, user_id=auth_user_id)
    # 2 leads for user B
    for i in range(2):
        await make_lead(db, user_id=user_b.id)
    await db.commit()

    r = await auth_client.get("/api/v1/leads/")
    assert r.status_code == 200
    assert r.json()["total"] == 3


async def test_list_leads_filter_by_lead_type(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """lead_type=b2b and lead_type=b2c filters work independently."""
    await make_lead(db, user_id=auth_user_id, lead_type="b2b")
    await make_lead(db, user_id=auth_user_id, lead_type="b2b")
    await make_lead(db, user_id=auth_user_id, lead_type="b2c")
    await make_lead(db, user_id=auth_user_id, lead_type="b2c")
    await db.commit()

    r_b2b = await auth_client.get("/api/v1/leads/?lead_type=b2b")
    r_b2c = await auth_client.get("/api/v1/leads/?lead_type=b2c")

    assert r_b2b.status_code == 200
    assert r_b2b.json()["total"] == 2

    assert r_b2c.status_code == 200
    assert r_b2c.json()["total"] == 2


async def test_list_leads_filter_by_tier(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """
    tier=hot filter returns only hot leads.
    HOT = score >= 85, so we pass tier=HOT to the enum.
    """
    await make_lead(db, user_id=auth_user_id, score=90, tier="hot")
    await make_lead(db, user_id=auth_user_id, score=70, tier="warm")
    await make_lead(db, user_id=auth_user_id, score=30, tier="cold")
    await db.commit()

    r = await auth_client.get("/api/v1/leads/?tier=hot")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["lead_tier"] == "hot"


async def test_list_leads_pagination(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """per_page=2 paginates correctly."""
    for _ in range(5):
        await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r1 = await auth_client.get("/api/v1/leads/?page=1&per_page=2")
    assert r1.status_code == 200
    body1 = r1.json()
    assert len(body1["items"]) == 2
    assert body1["total"] == 5
    assert body1["pages"] == 3

    r2 = await auth_client.get("/api/v1/leads/?page=3&per_page=2")
    body2 = r2.json()
    assert len(body2["items"]) == 1  # last page has only 1


# ── Status Update ──────────────────────────────────────────────────────────────

async def test_update_status_viewed(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """PATCH /leads/{id}/status to 'viewed' succeeds."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r = await auth_client.patch(
        f"/api/v1/leads/{lead.id}/status",
        json={"status": "viewed"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "viewed"


async def test_update_status_won(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """PATCH /leads/{id}/status to 'won' succeeds."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r = await auth_client.patch(
        f"/api/v1/leads/{lead.id}/status",
        json={"status": "won"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "won"


async def test_update_status_invalid(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """PATCH with an invalid status value returns 422."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r = await auth_client.patch(
        f"/api/v1/leads/{lead.id}/status",
        json={"status": "not_a_real_status"},
    )
    assert r.status_code == 422


async def test_update_status_wrong_user(
    auth_client: AsyncClient,
    db: AsyncSession,
):
    """User A cannot update User B's lead status."""
    user_b = await make_user(db, email="userb_status@test.com")
    lead_b = await make_lead(db, user_id=user_b.id)
    await db.commit()

    r = await auth_client.patch(
        f"/api/v1/leads/{lead_b.id}/status",
        json={"status": "viewed"},
    )
    assert r.status_code == 404


# ── Suppress ───────────────────────────────────────────────────────────────────

async def test_suppress_lead(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """POST /leads/{id}/suppress marks the lead as SUPPRESSED."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r = await auth_client.post(f"/api/v1/leads/{lead.id}/suppress")
    assert r.status_code == 200

    # Verify the lead is now suppressed via status endpoint
    r_check = await auth_client.get(f"/api/v1/leads/{lead.id}")
    assert r_check.status_code == 200
    assert r_check.json()["status"] == "suppressed"


async def test_suppress_removes_from_future_queries(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """
    After suppression, the lead's status is 'suppressed'.
    Filtering by status=new excludes it.
    """
    lead = await make_lead(db, user_id=auth_user_id, status=LeadStatus.NEW)
    await db.commit()

    await auth_client.post(f"/api/v1/leads/{lead.id}/suppress")

    r = await auth_client.get("/api/v1/leads/?status=new")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()["items"]]
    assert lead.id not in ids


# ── CSV Export ─────────────────────────────────────────────────────────────────

async def test_export_csv_headers(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """POST /leads/export/csv returns text/csv with the expected header columns."""
    for _ in range(3):
        await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r = await auth_client.post("/api/v1/leads/export/csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")

    # First line must be the header row
    first_line = r.text.split("\n")[0]
    assert "lead_id" in first_line
    assert "score" in first_line
    assert "company_name" in first_line


async def test_export_csv_empty(auth_client: AsyncClient):
    """POST /leads/export/csv with no leads returns 200 with a header-only CSV."""
    r = await auth_client.post("/api/v1/leads/export/csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    lines = [ln for ln in r.text.split("\n") if ln.strip()]
    # Exactly one line: the header row
    assert len(lines) == 1
