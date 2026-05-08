"""
ICP tests — AI builder + manual CRUD.

Claude is always mocked. The ICP builder talks to the DB (SQLite in-memory)
for record persistence; cache operations are mocked by conftest.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_icp, make_user

# ── Mock Claude ICP response ───────────────────────────────────────────────────
MOCK_ICP_DATA = {
    "suggested_name": "Manufacturing ICP Malaysia",
    "industries": ["Manufacturing", "Food & Beverage"],
    "job_titles": ["HR Manager", "General Manager"],
    "seniority_levels": ["manager", "director"],
    "company_sizes": ["10-50", "50-200"],
    "locations": ["Kuala Lumpur", "Selangor"],
    "keywords": ["group medical", "employee benefits"],
    "intent_signals": ["hiring", "expansion"],
    "search_queries": ["HR manager manufacturing KL"],
}

ICP_BUILD_PAYLOAD = {
    "description": "group medical insurance for manufacturing SMEs in Kuala Lumpur"
}

ICP_CREATE_PAYLOAD = {
    "name": "Healthcare ICP",
    "description": "Medical device sales for hospital procurement managers",
    "industries": ["Healthcare"],
    "job_titles": ["Procurement Manager"],
    "seniority_levels": ["manager"],
    "company_sizes": ["50-200", "200-500"],
    "locations": ["Kuala Lumpur"],
    "keywords": ["hospital", "procurement"],
    "intent_signals": ["expansion"],
    "search_queries": ["hospital procurement KL"],
}


# ── Build ICP (AI) ─────────────────────────────────────────────────────────────

async def test_build_icp_unauthenticated(client: AsyncClient):
    """Unauthenticated request to /icp/build returns 401. Claude must NOT be called."""
    mock_claude = AsyncMock(return_value=MOCK_ICP_DATA)
    with patch("app.icp.routes._call_claude", mock_claude):
        r = await client.post("/api/v1/icp/build", json=ICP_BUILD_PAYLOAD)
    assert r.status_code == 401
    mock_claude.assert_not_called()


async def test_build_icp_success(auth_client: AsyncClient):
    """Happy path: Claude returns a valid ICP dict → 201 with industries populated."""
    mock_claude = AsyncMock(return_value=MOCK_ICP_DATA)
    with patch("app.icp.routes._call_claude", mock_claude):
        r = await auth_client.post("/api/v1/icp/build", json=ICP_BUILD_PAYLOAD)
    assert r.status_code == 201
    body = r.json()
    assert "industries" in body
    assert "Manufacturing" in body["industries"]
    assert body["name"] == "Manufacturing ICP Malaysia"


async def test_build_icp_empty_description(auth_client: AsyncClient):
    """Description shorter than 10 chars fails Pydantic validation → 422."""
    r = await auth_client.post("/api/v1/icp/build", json={"description": ""})
    assert r.status_code == 422


async def test_build_icp_short_description(auth_client: AsyncClient):
    """A 9-char description is below the 10-char minimum → 422."""
    r = await auth_client.post("/api/v1/icp/build", json={"description": "too short"})
    assert r.status_code == 422


async def test_build_icp_uses_redis_cache(auth_client: AsyncClient):
    """
    Calling /icp/build twice with the same description hits Claude only ONCE.
    The second call is served from the in-memory cache mock.
    """
    # First call: cache miss (conftest mock returns None)
    # Second call: we'll simulate a cache hit by returning the saved ICP id

    icp_id_holder: list[str] = []

    original_set = AsyncMock(return_value=True)
    first_call_done = False

    async def smart_get_cached(key: str):
        """Return None on first call, ICP id on subsequent calls."""
        if not icp_id_holder:
            return None
        return {"id": icp_id_holder[0]}

    async def capture_set_cached(key, value, ttl=86400):
        if "id" in value:
            icp_id_holder.append(value["id"])
        return True

    mock_claude = AsyncMock(return_value=MOCK_ICP_DATA)
    with (
        patch("app.icp.routes._call_claude", mock_claude),
        patch("app.icp.routes.get_cached", side_effect=smart_get_cached),
        patch("app.icp.routes.set_cached", side_effect=capture_set_cached),
    ):
        r1 = await auth_client.post("/api/v1/icp/build", json=ICP_BUILD_PAYLOAD)
        assert r1.status_code == 201

        r2 = await auth_client.post("/api/v1/icp/build", json=ICP_BUILD_PAYLOAD)
        assert r2.status_code == 201

    # Claude must be called exactly once; second call hits cache
    assert mock_claude.call_count == 1


async def test_build_icp_claude_failure_graceful(auth_client: AsyncClient):
    """
    If the ICP builder's Claude call fails (via HTTPException), the endpoint
    returns the corresponding 4xx/5xx code — never a raw Python exception.

    We mock _call_claude to raise HTTPException(502) — exactly what it raises
    when Anthropic's API returns an error. FastAPI handles this gracefully.
    """
    from fastapi import HTTPException as FastAPIHTTPException

    mock_claude = AsyncMock(
        side_effect=FastAPIHTTPException(status_code=502, detail="AI service error: upstream timeout")
    )
    with patch("app.icp.routes._call_claude", mock_claude):
        r = await auth_client.post("/api/v1/icp/build", json=ICP_BUILD_PAYLOAD)
    assert r.status_code == 502


# ── Manual ICP CRUD ────────────────────────────────────────────────────────────

async def test_create_icp_manual(auth_client: AsyncClient):
    """POST /icp/ with a full payload returns 201 with an id."""
    r = await auth_client.post("/api/v1/icp/", json=ICP_CREATE_PAYLOAD)
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["name"] == ICP_CREATE_PAYLOAD["name"]


async def test_list_icps_empty(auth_client: AsyncClient):
    """GET /icp/ for a fresh user returns empty list."""
    r = await auth_client.get("/api/v1/icp/")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_icps_returns_created(auth_client: AsyncClient):
    """After creating two ICPs, GET /icp/ returns total == 2."""
    p2 = {**ICP_CREATE_PAYLOAD, "name": "ICP Two"}
    await auth_client.post("/api/v1/icp/", json=ICP_CREATE_PAYLOAD)
    await auth_client.post("/api/v1/icp/", json=p2)
    r = await auth_client.get("/api/v1/icp/")
    assert r.status_code == 200
    assert r.json()["total"] == 2


async def test_get_icp_by_id(auth_client: AsyncClient, db: AsyncSession, auth_user_id: str):
    """GET /icp/{id} returns the correct record."""
    icp = await make_icp(db, user_id=auth_user_id)
    await db.commit()
    r = await auth_client.get(f"/api/v1/icp/{icp.id}")
    assert r.status_code == 200
    assert r.json()["id"] == icp.id


async def test_get_icp_wrong_user(
    auth_client: AsyncClient,
    engine,
    db: AsyncSession,
):
    """
    User B must not see User A's ICP.
    We create a separate user directly and create their ICP via factory.
    Then user A tries to GET it → 404.
    """
    user_b = await make_user(db, email="userb@isolation.test")
    icp_b = await make_icp(db, user_id=user_b.id)
    await db.commit()

    # auth_client is logged in as user A
    r = await auth_client.get(f"/api/v1/icp/{icp_b.id}")
    assert r.status_code == 404


async def test_delete_icp(auth_client: AsyncClient, db: AsyncSession, auth_user_id: str):
    """
    DELETE /icp/{id} soft-deletes (sets is_active=False).
    The ICP no longer appears in GET /icp/ list.
    (GET /icp/{id} returns the record because it doesn't filter by is_active.)
    """
    icp = await make_icp(db, user_id=auth_user_id)
    await db.commit()

    r_del = await auth_client.delete(f"/api/v1/icp/{icp.id}")
    assert r_del.status_code == 204

    # Soft-delete: must NOT appear in the list any more
    r_list = await auth_client.get("/api/v1/icp/")
    ids = [i["id"] for i in r_list.json()["items"]]
    assert icp.id not in ids


async def test_delete_icp_wrong_user(auth_client: AsyncClient, db: AsyncSession):
    """User A must not be able to delete User B's ICP."""
    user_b = await make_user(db, email="userb_del@isolation.test")
    icp_b = await make_icp(db, user_id=user_b.id)
    await db.commit()

    r = await auth_client.delete(f"/api/v1/icp/{icp_b.id}")
    assert r.status_code == 404


async def test_get_icp_nonexistent(auth_client: AsyncClient):
    """GET /icp/nonexistent-id returns 404."""
    r = await auth_client.get("/api/v1/icp/does-not-exist-uuid")
    assert r.status_code == 404
