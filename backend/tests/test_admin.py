"""
Admin API tests — RBAC, stats, users, system health, lead quality.

Uses SQLite in-memory DB + httpx AsyncClient (see backend/conftest.py).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models import ZLUser
from tests.factories import make_lead, make_user


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def admin_client(client: AsyncClient, db):
    admin = await make_user(
        db,
        email="admin@example.com",
        plan="pro",
    )
    admin.role = "admin"
    await db.flush()
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "TestPass123!"},
    )
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
async def agent_client(client: AsyncClient, db):
    await make_user(db, email="agent@example.com")
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "agent@example.com", "password": "TestPass123!"},
    )
    assert r.status_code == 200, r.text
    return client


# ── RBAC ──────────────────────────────────────────────────────────────────────


async def test_admin_stats_requires_admin(agent_client: AsyncClient):
    r = await agent_client.get("/api/v1/admin/stats")
    assert r.status_code == 403


async def test_admin_users_requires_admin(agent_client: AsyncClient):
    r = await agent_client.get("/api/v1/admin/users")
    assert r.status_code == 403


async def test_admin_system_requires_admin(agent_client: AsyncClient):
    r = await agent_client.get("/api/v1/admin/system/health")
    assert r.status_code == 403


async def test_unauthenticated_cannot_access_admin(client: AsyncClient):
    r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 401


# ── Stats ─────────────────────────────────────────────────────────────────────


async def test_admin_stats_returns_correct_counts(admin_client: AsyncClient, db):
    for i in range(3):
        await make_user(db, email=f"statsuser{i}@example.com")
    res_u0 = await db.execute(
        select(ZLUser).where(ZLUser.email == "statsuser0@example.com")
    )
    u0 = res_u0.scalar_one_or_none()
    assert u0 is not None
    for _ in range(3):
        await make_lead(db, user_id=u0.id, lead_type="b2b")
    for _ in range(2):
        await make_lead(db, user_id=u0.id, lead_type="b2c")

    r = await admin_client.get("/api/v1/admin/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_users"] >= 3
    assert data["total_b2b_leads"] >= 3
    assert data["total_b2c_leads"] >= 2


async def test_admin_stats_hot_leads_count(admin_client: AsyncClient, db):
    u = await make_user(db, email="hotlead@example.com")
    for _ in range(2):
        await make_lead(db, user_id=u.id, score=90, tier="hot")
    for _ in range(3):
        await make_lead(db, user_id=u.id, score=50, tier="warm")

    r = await admin_client.get("/api/v1/admin/stats")
    assert r.status_code == 200
    assert r.json()["hot_leads_total"] >= 2


async def test_admin_stats_average_score(admin_client: AsyncClient, db):
    u = await make_user(db, email="avgscore@example.com")
    for score in (60, 80, 100):
        await make_lead(db, user_id=u.id, score=score)

    r = await admin_client.get("/api/v1/admin/stats")
    assert r.status_code == 200
    avg = r.json()["average_lead_score"]
    assert isinstance(avg, float)
    assert 60 <= avg <= 100


# ── User management ────────────────────────────────────────────────────────────


async def test_admin_list_users(admin_client: AsyncClient, db):
    for i in range(5):
        await make_user(db, email=f"listu{i}@example.com")

    r = await admin_client.get("/api/v1/admin/users")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["items"], list)
    assert body["total"] >= 5


async def test_admin_list_users_search(admin_client: AsyncClient, db):
    await make_user(db, email="searchme@example.com")

    r = await admin_client.get("/api/v1/admin/users", params={"search": "searchme"})
    assert r.status_code == 200
    emails = [x["email"] for x in r.json()["items"]]
    assert any("searchme" in e for e in emails)


async def test_admin_get_user_detail(admin_client: AsyncClient, db):
    u = await make_user(db, email="detail@example.com")
    for _ in range(3):
        await make_lead(db, user_id=u.id)

    r = await admin_client.get(f"/api/v1/admin/users/{u.id}")
    assert r.status_code == 200
    data = r.json()
    assert "user" in data and "leads" in data and "icps" in data
    assert data["user"]["lead_count"] == 3


async def test_admin_update_user_plan(admin_client: AsyncClient, db):
    u = await make_user(db, email="planup@example.com", plan="starter")

    r = await admin_client.patch(
        f"/api/v1/admin/users/{u.id}",
        json={"plan": "growth"},
    )
    assert r.status_code == 200
    assert r.json()["plan"] == "growth"


async def test_admin_update_user_role(admin_client: AsyncClient, db):
    u = await make_user(db, email="roleup@example.com")

    r = await admin_client.patch(
        f"/api/v1/admin/users/{u.id}",
        json={"role": "owner"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "owner"


async def test_admin_deactivate_user(admin_client: AsyncClient, client: AsyncClient, db):
    u = await make_user(db, email="deact@example.com")

    r = await admin_client.patch(
        f"/api/v1/admin/users/{u.id}",
        json={"is_active": False},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "deact@example.com", "password": "TestPass123!"},
    )
    assert r2.status_code == 401


async def test_admin_reset_password(admin_client: AsyncClient, client: AsyncClient, db):
    u = await make_user(db, email="resetpw@example.com")

    r = await admin_client.post(
        f"/api/v1/admin/users/{u.id}/reset-password",
        json={"new_password": "NewPass456!"},
    )
    assert r.status_code == 200

    r2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "resetpw@example.com", "password": "NewPass456!"},
    )
    assert r2.status_code == 200


async def test_admin_delete_user_soft(admin_client: AsyncClient, db):
    u = await make_user(db, email="softdel@example.com")
    uid = u.id

    r = await admin_client.delete(f"/api/v1/admin/users/{uid}")
    assert r.status_code == 204

    r2 = await admin_client.get("/api/v1/admin/users", params={"search": "softdel"})
    assert r2.status_code == 200
    items = r2.json()["items"]
    target = next((x for x in items if x["id"] == uid), None)
    assert target is not None
    assert target["is_active"] is False

    cnt = (
        await db.execute(select(func.count()).select_from(ZLUser).where(ZLUser.id == uid))
    ).scalar()
    assert cnt == 1


async def test_admin_cannot_delete_self(admin_client: AsyncClient, db):
    r_me = await admin_client.get("/api/v1/auth/me")
    assert r_me.status_code == 200
    admin_id = r_me.json()["id"]

    r = await admin_client.delete(f"/api/v1/admin/users/{admin_id}")
    assert r.status_code == 400
    assert "Cannot delete your own account" in r.json().get("detail", "")


# ── System health ─────────────────────────────────────────────────────────────


async def test_system_health_returns_all_services(admin_client: AsyncClient):
    r = await admin_client.get("/api/v1/admin/system/health")
    assert r.status_code == 200
    data = r.json()
    for key in ("postgresql", "redis", "elasticsearch"):
        assert key in data
        svc = data[key]
        assert "status" in svc
        assert "latency_ms" in svc


async def test_system_health_postgresql_is_healthy(admin_client: AsyncClient):
    r = await admin_client.get("/api/v1/admin/system/health")
    assert r.status_code == 200
    assert r.json()["postgresql"]["status"] == "healthy"


async def test_system_health_unavailable_service_doesnt_crash(
    admin_client: AsyncClient, monkeypatch
):
    class FakeEs:
        async def info(self):
            raise ConnectionError("es unavailable")

        async def count(self, index=""):
            raise ConnectionError("es unavailable")

    monkeypatch.setattr(
        "app.search.elasticsearch_client.get_client",
        lambda: FakeEs(),
    )

    r = await admin_client.get("/api/v1/admin/system/health")
    assert r.status_code == 200
    assert r.json()["elasticsearch"]["status"] == "down"


# ── Lead quality ──────────────────────────────────────────────────────────────


async def test_lead_quality_report_structure(admin_client: AsyncClient):
    r = await admin_client.get("/api/v1/admin/leads/quality-report")
    assert r.status_code == 200
    data = r.json()
    assert "email_verified_pct" in data
    assert "score_distribution" in data
    assert "hot" in data["score_distribution"]
    for pct_key in ("email_verified_pct", "phone_present_pct", "duplicate_rate"):
        v = data[pct_key]
        assert 0.0 <= v <= 100.0


async def test_lead_quality_with_no_leads(admin_client: AsyncClient):
    r = await admin_client.get("/api/v1/admin/leads/quality-report")
    assert r.status_code == 200
    data = r.json()
    assert data["total_leads"] == 0
    assert data["email_verified_pct"] == 0.0
    assert data["phone_present_pct"] == 0.0
    assert data["duplicate_rate"] == 0.0
    assert data["leads_without_contact"] == 0
    for k, v in data["score_distribution"].items():
        assert v == 0, k


# ── Role isolation ───────────────────────────────────────────────────────────


async def test_agent_cannot_see_other_users_data(client: AsyncClient, db):
    await make_user(db, email="usera_iso@example.com")
    await make_user(db, email="userb_iso@example.com")
    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "usera_iso@example.com", "password": "TestPass123!"},
    )
    assert r_login.status_code == 200

    r_users = await client.get("/api/v1/admin/users")
    assert r_users.status_code == 403
    r_leads = await client.get("/api/v1/admin/leads")
    assert r_leads.status_code == 403


async def test_owner_cannot_access_admin_panel(client: AsyncClient, db):
    u = await make_user(db, email="ownerpane@example.com")
    u.role = "owner"
    await db.flush()

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "ownerpane@example.com", "password": "TestPass123!"},
    )
    assert r.status_code == 200

    r2 = await client.get("/api/v1/admin/stats")
    assert r2.status_code == 403


async def test_admin_can_see_all_leads(admin_client: AsyncClient, db):
    ua = await make_user(db, email="alleads_a@example.com")
    ub = await make_user(db, email="alleads_b@example.com")
    for _ in range(3):
        await make_lead(db, user_id=ua.id)
    for _ in range(2):
        await make_lead(db, user_id=ub.id)

    r = await admin_client.get("/api/v1/admin/leads")
    assert r.status_code == 200
    assert r.json()["total"] >= 5
