"""Hybrid lead search — merges PostgreSQL, Elasticsearch, and Pinecone.

Execution order:
  1. Parse natural-language query → structured filters + semantic_query
  2. Run all three searches in parallel (asyncio.gather)
  3. Merge and deduplicate results by lead_id
  4. Re-rank using a weighted formula
  5. Return top-N lead_ids in final_score order

Individual search failures are swallowed — an empty list is returned for
the failing source so the merged result degrades gracefully rather than
crashing.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ZLCompany, ZLLead, ZLPerson
from app.search.elasticsearch_client import search_leads as es_search
from app.search.intent_parser import parse_lead_query
from app.search.pinecone_client import search_similar_leads


# ── Individual source adapters ────────────────────────────────────────────────


async def _postgres_search(
    filters: dict[str, Any],
    user_id: str,
    db: AsyncSession,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Query zl_leads joined with zl_people + zl_companies and apply
    structured filters extracted by the intent parser.

    Returns list of dicts with lead_id, lead_score, industry, location.
    """
    try:
        stmt = (
            select(ZLLead)
            .options(selectinload(ZLLead.person), selectinload(ZLLead.company))
            .where(ZLLead.user_id == user_id)
        )

        # ── Numeric filters ────────────────────────────────────────────────────
        min_score = filters.get("min_score")
        if isinstance(min_score, (int, float)):
            stmt = stmt.where(ZLLead.lead_score >= int(min_score))

        max_score = filters.get("max_score")
        if isinstance(max_score, (int, float)):
            stmt = stmt.where(ZLLead.lead_score <= int(max_score))

        stmt = stmt.order_by(ZLLead.lead_score.desc()).limit(limit * 2)

        result = await db.execute(stmt)
        leads = result.scalars().unique().all()

        # ── In-Python filters (joined tables) ─────────────────────────────────
        industry_filter = (filters.get("industry") or "").lower().strip()
        location_filter = (filters.get("location") or "").lower().strip()
        lead_type_filter = (filters.get("lead_type") or "").lower().strip()
        insurance_filter = (filters.get("insurance_type") or "").lower().strip()

        out: list[dict[str, Any]] = []
        for lead in leads:
            company: ZLCompany | None = lead.company

            if industry_filter and company:
                if industry_filter not in (company.industry or "").lower():
                    continue

            if location_filter and company:
                city    = (company.city or "").lower()
                country = (company.country or "").lower()
                if location_filter not in city and location_filter not in country:
                    continue

            if lead_type_filter:
                # B2B = has company, B2C = no company / has person only
                is_b2b = company is not None
                if lead_type_filter == "b2b" and not is_b2b:
                    continue
                if lead_type_filter == "b2c" and is_b2b:
                    continue

            if insurance_filter:
                product = (lead.recommended_product or "").lower()
                if insurance_filter not in product:
                    continue

            # Company size filters (uses company.employees field if present)
            size_min = filters.get("company_size_min")
            size_max = filters.get("company_size_max")
            if (size_min or size_max) and company:
                emp = getattr(company, "employee_count", None)
                if isinstance(emp, int):
                    if size_min and emp < int(size_min):
                        continue
                    if size_max and emp > int(size_max):
                        continue

            city_str = str(company.city) if company and company.city is not None else ""
            country_str = str(company.country) if company and company.country is not None else ""
            location_str = f"{city_str}, {country_str}".strip(", ") or None

            out.append({
                "lead_id":    str(lead.id),
                "lead_score": lead.lead_score or 0,
                "industry":   str(company.industry) if company and company.industry is not None else None,
                "location":   location_str,
                "source":     "postgresql",
            })

        return out[:limit]

    except Exception as exc:
        logger.warning(f"Hybrid search: PostgreSQL source failed: {exc}")
        return []


async def _elasticsearch_search(
    filters: dict[str, Any],
    user_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Build a search term from available text filters and query ES.

    Returns list of {lead_id, score}.
    """
    try:
        # Build a composite text query from available filters
        terms: list[str] = []
        for key in ("industry", "location", "insurance_type"):
            val = filters.get(key)
            if val:
                terms.append(str(val))
        semantic = filters.get("semantic_query", "")
        if semantic:
            terms.append(semantic)

        query_text = " ".join(terms).strip()
        if not query_text:
            return []

        hits = await es_search(query_text, size=limit)
        return [
            {
                "lead_id": hit.get("id", ""),
                "lead_score": hit.get("lead_score", 0),
                "score":  float(hit.get("lead_score", 0)) / 100,
                "source": "elasticsearch",
            }
            for hit in hits
            if hit.get("id")
        ]

    except Exception as exc:
        logger.warning(f"Hybrid search: Elasticsearch source failed: {exc}")
        return []


async def _pinecone_search(
    semantic_query: str,
    user_id: str,
    filters: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    """
    Embed semantic_query and query Pinecone with user-scoped filters.

    Returns list of {lead_id, score}.
    """
    try:
        if not semantic_query:
            return []

        # Build Pinecone metadata filter from intent filters
        pinecone_filters: dict[str, Any] = {}
        if filters.get("lead_type"):
            pinecone_filters["lead_type"] = {"$eq": filters["lead_type"]}
        if filters.get("industry"):
            pinecone_filters["industry"] = {"$eq": filters["industry"]}
        if filters.get("location"):
            pinecone_filters["location"] = {"$eq": filters["location"]}
        if filters.get("min_score"):
            pinecone_filters["lead_score"] = {"$gte": int(filters["min_score"])}

        matches = await search_similar_leads(
            query_text=semantic_query,
            user_id=user_id,
            top_k=limit,
            filters=pinecone_filters if pinecone_filters else None,
        )
        return [
            {
                "lead_id":    m["id"],
                "lead_score": int(m["metadata"].get("lead_score", 0)),
                "score":      float(m["score"]),
                "source":     "pinecone",
            }
            for m in matches
            if m.get("id")
        ]

    except Exception as exc:
        logger.warning(f"Hybrid search: Pinecone source failed: {exc}")
        return []


# ── Public entry point ────────────────────────────────────────────────────────


async def hybrid_lead_search(
    query: str,
    user_id: str,
    db: AsyncSession,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Run a 3-source hybrid search and return merged, re-ranked lead_ids.

    Steps:
      A. Parse query → structured filters + semantic_query
      B. Run PostgreSQL, Elasticsearch, Pinecone searches in parallel
      C. Merge results; deduplicate by lead_id; track contributing sources
      D. Re-rank with weighted formula
      E. Return top ``limit`` dicts sorted by final_score desc

    Each dict contains at minimum:
      lead_id, lead_score, final_score, sources (list)

    Never raises — returns an empty list on total failure.
    """
    try:
        # ── A: Intent parsing ─────────────────────────────────────────────────
        filters = await parse_lead_query(query)
        semantic_query: str = filters.get("semantic_query") or query

        # ── B: Parallel search ────────────────────────────────────────────────
        pg_task   = _postgres_search(filters, user_id, db, limit)
        es_task   = _elasticsearch_search(filters, user_id, limit)
        pin_task  = _pinecone_search(semantic_query, user_id, filters, limit)

        pg_results, es_results, pinecone_results = await asyncio.gather(
            pg_task, es_task, pin_task,
            return_exceptions=False,  # individual handlers already catch exceptions
        )

        logger.debug(
            f"Hybrid search: pg={len(pg_results)} "
            f"es={len(es_results)} "
            f"pinecone={len(pinecone_results)}"
        )

        # ── C: Merge + deduplicate ────────────────────────────────────────────
        merged: dict[str, dict[str, Any]] = {}

        for r in pg_results:
            lead_id = r["lead_id"]
            merged[lead_id] = {
                **r,
                "sources":  ["postgresql"],
                "pg_score": float(r.get("lead_score", 0)) / 100,
            }

        for r in es_results:
            lead_id = r["lead_id"]
            if lead_id in merged:
                merged[lead_id]["sources"].append("elasticsearch")
                merged[lead_id]["es_score"] = float(r.get("score", 0))
            else:
                merged[lead_id] = {
                    **r,
                    "sources":  ["elasticsearch"],
                    "es_score": float(r.get("score", 0)),
                }

        for r in pinecone_results:
            lead_id = r["lead_id"]
            if lead_id in merged:
                merged[lead_id]["sources"].append("pinecone")
                merged[lead_id]["pinecone_score"] = float(r.get("score", 0))
            else:
                merged[lead_id] = {
                    **r,
                    "sources":        ["pinecone"],
                    "pinecone_score": float(r.get("score", 0)),
                }

        # ── D: Re-rank ────────────────────────────────────────────────────────
        # final_score = (lead_score/100 × 0.40)        — absolute lead quality
        #             + (multi-source bonus   × 0.35)  — cross-validated signal
        #             + (pinecone_score       × 0.25)  — semantic relevance
        for data in merged.values():
            lead_score_norm  = data.get("lead_score", 50) / 100
            multi_src_bonus  = 0.35 if len(data["sources"]) >= 2 else 0.15
            semantic_contrib = data.get("pinecone_score", 0.0) * 0.25

            data["final_score"] = round(
                lead_score_norm * 0.40 + multi_src_bonus + semantic_contrib,
                4,
            )

        # ── E: Sort and cap ───────────────────────────────────────────────────
        sorted_leads = sorted(
            merged.values(),
            key=lambda x: x["final_score"],
            reverse=True,
        )[:limit]

        return sorted_leads

    except Exception as exc:
        logger.error(f"Hybrid search: total failure for user {user_id}: {exc}")
        return []
