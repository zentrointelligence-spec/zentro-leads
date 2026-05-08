"""
Pipeline CRM tests.

The pipeline entries link users to leads. All DB setup goes through
factories; HTTP calls go through the authenticated test client.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_company, make_lead, make_person, make_pipeline_entry, make_user


# ── Add to Pipeline ────────────────────────────────────────────────────────────

async def test_add_lead_to_pipeline(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """POST /pipeline/ with a valid lead_id returns 201."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r = await auth_client.post(
        "/api/v1/pipeline/",
        json={"lead_id": lead.id, "stage": "new"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["lead_id"] == lead.id
    assert body["stage"] == "new"


async def test_add_lead_idempotent(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """
    Adding the same lead to the pipeline twice should succeed both times.
    The second call returns the existing entry (no duplicate created).
    """
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r1 = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead.id, "stage": "new"}
    )
    assert r1.status_code == 201

    r2 = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead.id, "stage": "new"}
    )
    # Second call returns the existing entry — route returns 201 either way
    assert r2.status_code == 201

    # List the pipeline — the lead appears exactly ONCE
    r_list = await auth_client.get("/api/v1/pipeline/")
    assert r_list.status_code == 200
    lead_ids = [e["lead_id"] for e in r_list.json()["entries"]]
    assert lead_ids.count(lead.id) == 1


async def test_add_nonexistent_lead_returns_404(auth_client: AsyncClient):
    """Attempting to add a lead that doesn't exist returns 404."""
    r = await auth_client.post(
        "/api/v1/pipeline/",
        json={"lead_id": "00000000-fake-fake-fake-000000000000", "stage": "new"},
    )
    assert r.status_code == 404


# ── Move Stage ─────────────────────────────────────────────────────────────────

async def test_move_stage(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """PATCH /pipeline/{id} moves the entry to the new stage."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r_add = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead.id, "stage": "new"}
    )
    assert r_add.status_code == 201
    entry_id = r_add.json()["id"]

    r_move = await auth_client.patch(
        f"/api/v1/pipeline/{entry_id}",
        json={"stage": "contacted"},
    )
    assert r_move.status_code == 200
    assert r_move.json()["stage"] == "contacted"

    # Confirm via list
    r_list = await auth_client.get("/api/v1/pipeline/")
    stages = {e["id"]: e["stage"] for e in r_list.json()["entries"]}
    assert stages[entry_id] == "contacted"


async def test_move_stage_invalid(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """PATCH with an invalid stage name is rejected → 422."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r_add = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead.id, "stage": "new"}
    )
    entry_id = r_add.json()["id"]

    r = await auth_client.patch(
        f"/api/v1/pipeline/{entry_id}",
        json={"stage": "not_a_real_stage"},
    )
    assert r.status_code == 422


async def test_move_stage_to_all_valid_stages(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """All six valid stage values are accepted by PATCH."""
    valid_stages = ["new", "contacted", "qualified", "proposal", "closed_won", "closed_lost"]
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r_add = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead.id, "stage": "new"}
    )
    entry_id = r_add.json()["id"]

    for stage in valid_stages:
        r = await auth_client.patch(
            f"/api/v1/pipeline/{entry_id}", json={"stage": stage}
        )
        assert r.status_code == 200, f"Stage '{stage}' was rejected"
        assert r.json()["stage"] == stage


# ── Remove from Pipeline ───────────────────────────────────────────────────────

async def test_remove_from_pipeline(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """DELETE /pipeline/{id} → 204; entry no longer appears in list."""
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r_add = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead.id, "stage": "new"}
    )
    entry_id = r_add.json()["id"]

    r_del = await auth_client.delete(f"/api/v1/pipeline/{entry_id}")
    assert r_del.status_code == 204

    r_list = await auth_client.get("/api/v1/pipeline/")
    ids = [e["id"] for e in r_list.json()["entries"]]
    assert entry_id not in ids


async def test_remove_does_not_delete_lead(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """
    Deleting a pipeline entry must NOT delete the underlying lead.
    After removal, GET /leads/{id} still returns 200.
    """
    lead = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    r_add = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead.id, "stage": "new"}
    )
    entry_id = r_add.json()["id"]
    await auth_client.delete(f"/api/v1/pipeline/{entry_id}")

    r_lead = await auth_client.get(f"/api/v1/leads/{lead.id}")
    assert r_lead.status_code == 200, "Deleting pipeline entry must not delete the lead"


# ── Isolation ──────────────────────────────────────────────────────────────────

async def test_pipeline_isolation(
    auth_client: AsyncClient,
    db: AsyncSession,
    auth_user_id: str,
):
    """
    User A adds a lead. After logging in as User B, the pipeline is empty —
    User B cannot see User A's entries.
    """
    lead_a = await make_lead(db, user_id=auth_user_id)
    await db.commit()

    # User A adds their lead to pipeline
    r_add = await auth_client.post(
        "/api/v1/pipeline/", json={"lead_id": lead_a.id, "stage": "new"}
    )
    assert r_add.status_code == 201

    # Create User B directly in the DB — avoids extra HTTP register calls
    user_b = await make_user(db, email="userb_pipe@example.com")
    await db.commit()

    # Log in as User B (login has a higher rate limit than register)
    r_login_b = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "userb_pipe@example.com", "password": "TestPass123!"},
    )
    assert r_login_b.status_code == 200, r_login_b.text

    # Client is now authenticated as User B — pipeline must be empty
    r_pipe = await auth_client.get("/api/v1/pipeline/")
    assert r_pipe.status_code == 200
    assert r_pipe.json()["total"] == 0


# ── List Pipeline ──────────────────────────────────────────────────────────────

async def test_list_pipeline_empty(auth_client: AsyncClient):
    """A fresh user has an empty pipeline."""
    r = await auth_client.get("/api/v1/pipeline/")
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["entries"] == []


async def test_list_pipeline_unauthenticated(client: AsyncClient):
    """GET /pipeline/ without auth returns 401."""
    r = await client.get("/api/v1/pipeline/")
    assert r.status_code == 401
