"""Pinecone vector search client for Zentro Leads.

All public functions are fire-and-forget safe — any error is caught,
logged, and swallowed so lead generation is never blocked.

Embedding model: text-embedding-3-small (1536 dimensions, via OpenAI).
Index metric:    cosine
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from loguru import logger

from app.config import settings

# ── Lazy singletons ────────────────────────────────────────────────────────────

_pinecone_index: Any = None  # pinecone.Index


def _is_configured() -> bool:
    """Return True only when both Pinecone and OpenAI keys are set."""
    return bool(settings.PINECONE_API_KEY) and bool(settings.OPENAI_API_KEY)


# ── Index bootstrap ────────────────────────────────────────────────────────────

async def get_pinecone_index() -> Any:
    """
    Return the Pinecone index singleton.

    Creates the index (dimension=1536, metric=cosine, serverless on AWS us-east-1)
    if it doesn't already exist. Returns None if credentials are not configured
    — callers must check the return value before using it.
    """
    global _pinecone_index

    if not _is_configured():
        logger.debug("Pinecone not configured — skipping index initialisation")
        return None

    if _pinecone_index is not None:
        return _pinecone_index

    try:
        # Import here so the module loads even when pinecone-client is not installed
        from pinecone import Pinecone, ServerlessSpec  # type: ignore[import]

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index_name = settings.PINECONE_INDEX_NAME

        existing = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing:
            pc.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Pinecone: created index '{index_name}'")
        else:
            logger.debug(f"Pinecone: index '{index_name}' already exists")

        _pinecone_index = pc.Index(index_name)
        return _pinecone_index

    except Exception as exc:
        logger.warning(f"Pinecone: index initialisation failed: {exc}")
        return None


# ── Embedding generation ───────────────────────────────────────────────────────

async def generate_lead_embedding(lead_text: str) -> list[float]:
    """
    Generate a 1536-dimensional embedding for ``lead_text`` using
    OpenAI text-embedding-3-small via the AsyncOpenAI client.

    Raises on failure — callers that want fire-and-forget should wrap
    the call in a try/except (see ``upsert_lead_embedding``).
    """
    from openai import AsyncOpenAI  # type: ignore[import]

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=lead_text,
    )
    return response.data[0].embedding


# ── Text builder ───────────────────────────────────────────────────────────────

def build_lead_text(lead: dict[str, Any]) -> str:
    """
    Produce a rich, descriptive text representation of a lead for embedding.

    The more context packed in here, the more semantically meaningful the
    resulting vector is — improving similarity search quality.
    """
    parts: list[str] = []

    if company := lead.get("company_name"):
        parts.append(f"Company: {company}.")

    if industry := lead.get("industry"):
        parts.append(f"Industry: {industry}.")

    if location := lead.get("location"):
        parts.append(f"Location: {location}.")

    if job_title := lead.get("job_title"):
        parts.append(f"Decision maker: {job_title}.")

    if lead_type := lead.get("lead_type"):
        parts.append(f"Lead type: {lead_type.upper()}.")

    if insurance_type := lead.get("insurance_type"):
        parts.append(f"Insurance need: {insurance_type}.")

    # Intent / buying signals
    signals = lead.get("insurance_signals") or lead.get("intent_signals")
    if signals:
        if isinstance(signals, list):
            parts.append(f"Buying signals: {', '.join(str(s) for s in signals)}.")
        else:
            parts.append(f"Buying signals: {signals}.")

    if score := lead.get("lead_score"):
        parts.append(f"Lead score: {score}/100.")

    if not parts:
        return "Unqualified business lead."
    return " ".join(parts)


# ── Upsert ─────────────────────────────────────────────────────────────────────

async def upsert_lead_embedding(
    lead_id: str,
    lead: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    """
    Generate an embedding for the lead and upsert it to Pinecone.

    This function is designed to be called with ``asyncio.create_task()``
    as a fire-and-forget background task. All errors are caught and logged
    — they never propagate to the caller.

    Args:
        lead_id:  UUID string of the zl_leads row (used as Pinecone vector ID).
        lead:     Dict with company_name, industry, location, job_title, etc.
        metadata: Dict stored alongside the vector for filtering queries.
                  Should contain at minimum user_id and lead_score.
    """
    if not _is_configured():
        return  # silently skip — no key configured

    try:
        index = await get_pinecone_index()
        if index is None:
            return

        lead_text  = build_lead_text(lead)
        embedding  = await generate_lead_embedding(lead_text)

        # Pinecone metadata values must be scalar — normalise to str/int/float/bool
        clean_meta: dict[str, Any] = {
            k: (str(v) if isinstance(v, (list, dict)) else v)
            for k, v in metadata.items()
            if v is not None
        }
        clean_meta["lead_id"] = lead_id  # always include for reverse lookup

        # Run the synchronous Pinecone SDK call in a thread so we don't block
        await asyncio.to_thread(
            index.upsert,
            vectors=[{"id": lead_id, "values": embedding, "metadata": clean_meta}],
        )
        logger.debug(f"Pinecone: upserted lead {lead_id}")

    except Exception as exc:
        logger.warning(f"Pinecone: failed to upsert lead {lead_id}: {exc}")


# ── Similarity search ──────────────────────────────────────────────────────────

async def search_similar_leads(
    query_text: str,
    user_id: str,
    top_k: int = 50,
    filters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Embed ``query_text`` and query Pinecone for the most similar leads
    belonging to ``user_id``.

    Args:
        query_text: Natural-language search string (e.g. "motor fleet SME KL").
        user_id:    Scopes results to this user's leads.
        top_k:      Maximum number of results to return.
        filters:    Extra Pinecone metadata filters merged with the user_id filter.

    Returns:
        List of ``{"id": str, "score": float, "metadata": dict}`` dicts,
        sorted descending by similarity score. Returns empty list on any error.
    """
    if not _is_configured():
        logger.debug("Pinecone search skipped — not configured")
        return []

    try:
        index = await get_pinecone_index()
        if index is None:
            return []

        embedding = await generate_lead_embedding(query_text)

        # Build filter dict — always scope to the requesting user
        pinecone_filter: dict[str, Any] = {"user_id": {"$eq": user_id}}
        if filters:
            pinecone_filter.update(filters)

        result = await asyncio.to_thread(
            index.query,
            vector=embedding,
            top_k=top_k,
            filter=pinecone_filter,
            include_metadata=True,
        )

        return [
            {
                "id":       match["id"],
                "score":    match["score"],
                "metadata": match.get("metadata", {}),
            }
            for match in result.get("matches", [])
        ]

    except Exception as exc:
        logger.warning(f"Pinecone: search failed: {exc}")
        return []


# ── Delete ─────────────────────────────────────────────────────────────────────

async def delete_lead_embedding(lead_id: str) -> None:
    """
    Remove a lead's vector from Pinecone. Safe to call even if the vector
    doesn't exist — errors are caught and logged, never raised.
    """
    if not _is_configured():
        return

    try:
        index = await get_pinecone_index()
        if index is None:
            return

        await asyncio.to_thread(index.delete, ids=[lead_id])
        logger.debug(f"Pinecone: deleted vector for lead {lead_id}")

    except Exception as exc:
        # Includes the case where the ID doesn't exist in Pinecone
        logger.debug(f"Pinecone: delete skipped for lead {lead_id}: {exc}")
