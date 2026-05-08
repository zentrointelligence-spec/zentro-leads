"""Async Elasticsearch client and leads index helpers for Zentro Leads.

Index name: zl_leads
All interactions are fire-and-forget — indexing errors are logged but
never raise to the caller so they never block lead generation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, UTC
from typing import Any, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from loguru import logger

from app.config import settings

# ── Index configuration ────────────────────────────────────────────────────────

LEADS_INDEX = "zl_leads"

LEADS_MAPPING: dict[str, Any] = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "company_name": {
                "type": "text",
                "analyzer": "standard",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "industry": {"type": "keyword"},
            "location": {"type": "keyword"},
            "lead_score": {"type": "integer"},
            "insurance_type": {"type": "keyword"},
            "lead_type": {"type": "keyword"},   # "b2b" or "b2c"
            "created_at": {"type": "date"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # single-node dev; set to 1 in production
    },
}

# ── Client singleton ───────────────────────────────────────────────────────────

_client: Optional[AsyncElasticsearch] = None


def get_client() -> AsyncElasticsearch:
    """Return the module-level Elasticsearch async client (lazy-initialised)."""
    global _client
    if _client is None:
        _client = AsyncElasticsearch(
            [settings.ELASTICSEARCH_URL],
            request_timeout=10,
            retry_on_timeout=True,
            max_retries=2,
        )
    return _client


async def close_client() -> None:
    """Close the client transport — call this on app shutdown."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


# ── Index bootstrap ────────────────────────────────────────────────────────────


async def ensure_leads_index() -> None:
    """Create the zl_leads index with mapping if it does not already exist.

    Safe to call on every startup — no-op when the index is already present.
    """
    from elasticsearch import BadRequestError as ESBadRequestError  # type: ignore[import]

    client = get_client()
    try:
        exists = await client.indices.exists(index=LEADS_INDEX)
        if not exists:
            await client.indices.create(index=LEADS_INDEX, body=LEADS_MAPPING)
            logger.info(f"Elasticsearch: created index '{LEADS_INDEX}'")
        else:
            logger.debug(f"Elasticsearch: index '{LEADS_INDEX}' already exists")
    except ESBadRequestError as exc:
        if "resource_already_exists_exception" in str(exc):
            logger.debug(f"Elasticsearch: index '{LEADS_INDEX}' already exists (race condition ignored)")
        else:
            logger.warning(f"Elasticsearch: could not ensure index '{LEADS_INDEX}': {exc}")
    except Exception as exc:
        logger.warning(f"Elasticsearch: could not ensure index '{LEADS_INDEX}': {exc}")


# ── Indexing ───────────────────────────────────────────────────────────────────


async def index_lead(
    *,
    lead_id: str,
    company_name: Optional[str],
    industry: Optional[str],
    location: Optional[str],
    lead_score: Optional[int],
    insurance_type: Optional[str],
    lead_type: Optional[str],
    created_at: Optional[datetime],
) -> None:
    """Index a single lead document in Elasticsearch.

    Called after a lead is persisted to PostgreSQL.  All errors are caught and
    logged — this must never raise to the caller.

    Args:
        lead_id: UUID of the zl_leads row (used as the ES document ID).
        company_name: Normalised company display name.
        industry: Freeform industry string (e.g. "Insurance").
        location: City or country string.
        lead_score: Integer 0–100.
        insurance_type: Product type derived by AI (e.g. "motor", "life").
        lead_type: "b2b" or "b2c".
        created_at: UTC datetime the lead was created.
    """
    doc: dict[str, Any] = {
        "id": lead_id,
        "company_name": company_name or "",
        "industry": industry or "",
        "location": location or "",
        "lead_score": lead_score or 0,
        "insurance_type": insurance_type or "",
        "lead_type": lead_type or "",
        "created_at": created_at.isoformat() if created_at else datetime.now(UTC).isoformat(),
    }
    client = get_client()
    try:
        await client.index(index=LEADS_INDEX, id=lead_id, document=doc)
        logger.debug(f"Elasticsearch: indexed lead {lead_id}")
    except Exception as exc:
        logger.warning(f"Elasticsearch: failed to index lead {lead_id}: {exc}")


async def delete_lead(lead_id: str) -> None:
    """Remove a lead document from the index when deleted from PostgreSQL."""
    client = get_client()
    try:
        await client.delete(index=LEADS_INDEX, id=lead_id)
        logger.debug(f"Elasticsearch: deleted lead {lead_id}")
    except NotFoundError:
        pass
    except Exception as exc:
        logger.warning(f"Elasticsearch: failed to delete lead {lead_id}: {exc}")


async def search_leads(
    query: str,
    *,
    size: int = 20,
) -> list[dict[str, Any]]:
    """Full-text search across company_name and industry fields.

    Returns a list of raw Elasticsearch hit sources.
    """
    client = get_client()
    try:
        resp = await client.search(
            index=LEADS_INDEX,
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["company_name^2", "industry", "location", "insurance_type"],
                        "fuzziness": "AUTO",
                    }
                },
                "sort": [{"lead_score": "desc"}],
                "size": size,
            },
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]
    except Exception as exc:
        logger.warning(f"Elasticsearch: search failed: {exc}")
        return []
