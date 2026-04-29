"""
Lead generation orchestrator — scrape, enrich, verify, score, persist, ZIMS sync.
"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.email.verifier import find_best_email
from app.models import (
    LeadSource,
    LeadTier,
    ZLCompany,
    ZLICP,
    ZLLead,
    ZLPerson,
    ZLSuppressionList,
    ZLUser,
)
from app.scraper.google_maps.scraper import scrape_google_maps
from app.scraper.website.scraper import scrape_company_website
from app.scoring.engine import (
    _infer_seniority_from_title,
    calculate_lead_score,
    generate_ai_outreach,
)
from app.sync.zims import push_lead_to_zims


def extract_domain(url: str | None) -> str | None:
    """
    Parse registrable-style host from URL.

    ``https://company.com/page`` → ``company.com``
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


async def check_suppression(
    email: str | None,
    domain: str | None,
    user_id: str,
    db: AsyncSession,
) -> bool:
    """
    Return True if email or domain appears on suppression list for this user
    or globally (``user_id`` NULL).
    """
    from sqlalchemy import and_, or_

    clauses: list[Any] = []
    if email:
        em = email.lower().strip()
        clauses.append(
            and_(ZLSuppressionList.value_type == "email", ZLSuppressionList.value == em)
        )
    if domain:
        dom = domain.lower().strip().lstrip("@")
        clauses.append(
            and_(ZLSuppressionList.value_type == "domain", ZLSuppressionList.value == dom)
        )
    if not clauses:
        return False

    stmt = (
        select(ZLSuppressionList)
        .where(
            or_(*clauses),
            or_(ZLSuppressionList.user_id == user_id, ZLSuppressionList.user_id.is_(None)),
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def upsert_company(data: dict[str, Any], db: AsyncSession) -> ZLCompany:
    """
    Insert or update a company row.

    Match priority: ``google_maps_id`` first, then ``domain``.
    """
    gid = data.get("google_maps_id")
    website = data.get("website")
    domain = extract_domain(website) if website else None

    existing: ZLCompany | None = None
    if gid:
        res = await db.execute(select(ZLCompany).where(ZLCompany.google_maps_id == gid))
        existing = res.scalar_one_or_none()
    if existing is None and domain:
        res = await db.execute(select(ZLCompany).where(ZLCompany.domain == domain))
        existing = res.scalar_one_or_none()

    if existing:
        existing.name = data.get("name") or existing.name
        if website:
            existing.website = website
        if domain:
            existing.domain = domain
        if data.get("industry") and not existing.industry:
            existing.industry = data.get("industry")
        if data.get("phone"):
            existing.phone = data.get("phone")
        if data.get("address"):
            existing.address = data.get("address")
        if data.get("city"):
            existing.city = data.get("city")
        if data.get("country"):
            existing.country = data.get("country")
        if data.get("google_rating") is not None:
            existing.google_rating = data.get("google_rating")
        if data.get("google_reviews") is not None:
            existing.google_reviews = data.get("google_reviews")
        if data.get("latitude") is not None:
            existing.latitude = data.get("latitude")
        if data.get("longitude") is not None:
            existing.longitude = data.get("longitude")
        existing.data_source = LeadSource.GOOGLE_MAPS
        await db.flush()
        return existing

    company = ZLCompany(
        name=data.get("name") or "Unknown",
        domain=domain,
        website=website,
        industry=data.get("industry"),
        phone=data.get("phone"),
        address=data.get("address"),
        city=data.get("city"),
        country=data.get("country"),
        google_maps_id=gid,
        google_rating=data.get("google_rating"),
        google_reviews=data.get("google_reviews"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        data_source=LeadSource.GOOGLE_MAPS,
    )
    db.add(company)
    await db.flush()
    return company


async def upsert_person(data: dict[str, Any], db: AsyncSession) -> ZLPerson:
    """
    Insert or update a person for a company.

    Match on ``full_name`` + ``company_id``. Upgrades email when confidence improves.
    """
    company_id = data["company_id"]
    full_name = data.get("full_name") or data.get("name") or "Unknown"
    res = await db.execute(
        select(ZLPerson).where(ZLPerson.company_id == company_id, ZLPerson.full_name == full_name)
    )
    existing = res.scalar_one_or_none()

    new_email = data.get("email")
    new_conf = float(data.get("email_confidence") or 0.0)
    new_verified = bool(data.get("email_verified", False))

    if existing:
        better = (new_email and new_conf > float(existing.email_confidence or 0.0)) or (
            new_email and new_conf == float(existing.email_confidence or 0.0) and new_verified
        )
        if better:
            existing.email = new_email
            existing.email_verified = new_verified
            existing.email_confidence = new_conf
            existing.email_source = data.get("email_source") or existing.email_source
        if data.get("job_title"):
            existing.job_title = data.get("job_title")
        if data.get("phone"):
            existing.phone = data.get("phone")
        if data.get("linkedin_url"):
            existing.linkedin_url = data.get("linkedin_url")
        if data.get("first_name"):
            existing.first_name = data.get("first_name")
        if data.get("last_name"):
            existing.last_name = data.get("last_name")
        if data.get("seniority"):
            existing.seniority = data.get("seniority")
        existing.data_source = data.get("data_source") or existing.data_source or LeadSource.WEBSITE
        await db.flush()
        return existing

    person = ZLPerson(
        company_id=company_id,
        full_name=full_name,
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        job_title=data.get("job_title"),
        seniority=data.get("seniority"),
        email=new_email,
        email_verified=new_verified,
        email_confidence=new_conf,
        email_source=data.get("email_source"),
        phone=data.get("phone"),
        linkedin_url=data.get("linkedin_url"),
        data_source=data.get("data_source") or LeadSource.WEBSITE,
    )
    db.add(person)
    await db.flush()
    return person


async def generate_leads_for_icp(user_id: str, icp_id: str, db: AsyncSession) -> dict[str, int]:
    """
    Full lead generation pipeline for one ICP.

    Scrapes companies, enriches via website, verifies email, scores, persists hot+
    leads, and schedules ZIMS push for HOT leads.
    """
    icp = await db.get(ZLICP, icp_id)
    if not icp or icp.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ICP not found.")

    user = await db.get(ZLUser, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.leads_used_this_month >= user.leads_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Monthly lead limit reached",
                "used": user.leads_used_this_month,
                "limit": user.leads_limit,
                "upgrade_url": "/dashboard/billing",
            },
        )

    counters: dict[str, int] = {
        "generated": 0,
        "skipped_existing": 0,
        "skipped_cold": 0,
        "skipped_suppressed": 0,
        "errors": 0,
        "hot": 0,
        "warm": 0,
        "potential": 0,
    }

    queries = (icp.search_queries or [])[:5] if icp.search_queries else []
    if not queries:
        if icp.industries and icp.locations:
            queries = [f"{icp.industries[0]} {icp.locations[0]}"]
            logger.info(f"ICP {icp_id}: no search_queries set — derived query from industries+locations: {queries}")
        else:
            queries = [icp.name]
            logger.warning(
                f"ICP {icp_id} ('{icp.name}') has no search_queries, industries, or locations. "
                f"Falling back to ICP name as search query. "
                f"Use POST /api/v1/icp/build to generate a properly populated ICP, "
                f"or PATCH the ICP to add search_queries/industries/locations before generating."
            )

    location = icp.locations[0] if icp.locations else ""
    logger.info(f"ICP {icp_id}: running {len(queries)} query/queries, location={location!r}, queries={queries}")

    for query in queries:
        try:
            companies = await scrape_google_maps(str(query), str(location), max_results=20)
        except Exception as exc:
            logger.error(f"Maps scrape failed: {exc}")
            counters["errors"] += 1
            continue

        for company_data in companies:
            try:
                company = await upsert_company(company_data, db)

                site_data: dict[str, Any] = {}
                if company.website:
                    site_data = await scrape_company_website(company.website)

                # Write social links back from the website scraper — these are the
                # only fields scrape_company_website actually returns beyond people/emails/phones.
                social = site_data.get("social") or {}
                if social.get("linkedin") and not company.linkedin_url:
                    company.linkedin_url = social["linkedin"]
                if social.get("facebook") and not company.facebook_url:
                    company.facebook_url = social["facebook"]
                if social.get("instagram") and not company.instagram_url:
                    company.instagram_url = social["instagram"]
                await db.flush()

                domain = company.domain or extract_domain(company.website)

                people = site_data.get("people") or []
                # No real people found — company row is stored for future enrichment
                # but we do not create phantom "Decision Maker" lead rows.
                if not people:
                    continue

                for person_data in people[:5]:
                    try:
                        raw_name = (person_data.get("name") or "").strip()
                        # Reject noise from heuristic extraction: need ≥3 chars, non-numeric.
                        if not raw_name or len(raw_name) < 3 or raw_name.isdigit():
                            continue
                        name_parts = raw_name.split(" ", 1)
                        first = name_parts[0] if name_parts else ""
                        last = name_parts[1] if len(name_parts) > 1 else ""

                        email_result: dict[str, Any] = {
                            "email": None,
                            "valid": False,
                            "confidence": 0.0,
                            "method": "none",
                        }
                        if first and last and domain:
                            email_result = await find_best_email(first, last, domain)
                        elif site_data.get("emails"):
                            email_result = {
                                "email": site_data["emails"][0],
                                "valid": True,
                                "confidence": 0.7,
                                "method": "website",
                            }

                        title_guess = person_data.get("title") or "Unknown"
                        seniority = _infer_seniority_from_title(title_guess)

                        person = await upsert_person(
                            {
                                "name": raw_name,
                                "full_name": raw_name,
                                "first_name": first,
                                "last_name": last,
                                "job_title": title_guess,
                                "seniority": seniority,
                                "company_id": company.id,
                                "email": email_result.get("email"),
                                "email_verified": bool(email_result.get("valid", False)),
                                "email_confidence": float(email_result.get("confidence", 0.0)),
                                "email_source": str(email_result.get("method") or "unknown"),
                                "phone": (site_data.get("phones") or [None])[0],
                                "linkedin_url": (site_data.get("social") or {}).get("linkedin"),
                                "data_source": LeadSource.WEBSITE,
                            },
                            db,
                        )

                        person_dict = {
                            "job_title": person.job_title or "",
                            "seniority": person.seniority or "",
                            "email": person.email,
                            "email_verified": person.email_verified,
                            "email_confidence": person.email_confidence,
                            "job_changed_at": person.job_changed_at,
                            "first_name": person.first_name,
                            "full_name": person.full_name,
                        }
                        company_dict = {
                            "industry": company.industry or "",
                            "employee_range": company.employee_range or "",
                            "is_hiring": company.is_hiring,
                            "in_the_news": company.in_the_news,
                            "funding_stage": company.funding_stage,
                            "name": company.name,
                            "city": company.city,
                            "country": company.country,
                        }
                        icp_dict = {
                            "industries": icp.industries or [],
                            "job_titles": icp.job_titles or [],
                            "seniority_levels": icp.seniority_levels or [],
                            "company_sizes": icp.company_sizes or [],
                            "intent_signals": icp.intent_signals or [],
                        }

                        score_result = calculate_lead_score(person_dict, company_dict, icp_dict)

                        # Store cold leads — they're real contacts and visible in the UI.
                        # Only skip the absolute floor: real person but literally zero score
                        # and no email (nothing to work with at all).
                        if score_result["score"] == 0 and not person.email:
                            counters["skipped_cold"] += 1
                            continue

                        if person.email:
                            sup = await check_suppression(
                                person.email,
                                company.domain,
                                user_id,
                                db,
                            )
                            if sup:
                                counters["skipped_suppressed"] += 1
                                continue

                        existing = await db.execute(
                            select(ZLLead).where(
                                ZLLead.user_id == user_id,
                                ZLLead.person_id == person.id,
                            ).limit(1)
                        )
                        if existing.scalar_one_or_none():
                            counters["skipped_existing"] += 1
                            continue

                        outreach: dict[str, str] = {}
                        if score_result["score"] >= 60:
                            signals = score_result["breakdown"].get("signals_detected", [])
                            outreach = await generate_ai_outreach(
                                person_dict,
                                company_dict,
                                icp.description or icp.name,
                                signals,
                            )

                        lead = ZLLead(
                            user_id=user_id,
                            icp_id=icp_id,
                            person_id=person.id,
                            company_id=company.id,
                            lead_score=score_result["score"],
                            lead_tier=LeadTier[score_result["tier"].upper()],
                            score_breakdown=score_result["breakdown"],
                            intent_signals=score_result["breakdown"].get("signals_detected", []),
                            source=LeadSource.GOOGLE_MAPS,
                            ai_whatsapp_msg=outreach.get("whatsapp_message"),
                            ai_email_subject=outreach.get("email_subject"),
                            ai_email_body=outreach.get("email_body"),
                            ai_linkedin_note=outreach.get("linkedin_note"),
                        )
                        db.add(lead)
                        await db.flush()

                        counters["generated"] += 1
                        tier_key = score_result["tier"]
                        if tier_key in counters:
                            counters[tier_key] += 1

                        if score_result["score"] >= 85:
                            asyncio.create_task(push_lead_to_zims(lead.id))

                    except Exception as exc:
                        logger.error(f"Person processing error: {exc}")
                        counters["errors"] += 1
                        continue

            except Exception as exc:
                logger.error(f"Company processing error: {exc}")
                counters["errors"] += 1
                continue

    icp.total_leads_generated = (icp.total_leads_generated or 0) + counters["generated"]
    user.leads_used_this_month = (user.leads_used_this_month or 0) + counters["generated"]
    await db.flush()
    return counters


async def run_lead_generation_job(user_id: str, icp_id: str) -> None:
    """
    Background-safe entrypoint that owns its own DB session and commit/rollback.
    """
    async with AsyncSessionLocal() as db:
        try:
            summary = await generate_leads_for_icp(user_id, icp_id, db)
            await db.commit()
            logger.info(f"Lead generation job finished for icp={icp_id}: {summary}")
        except HTTPException:
            await db.rollback()
            logger.warning(f"Lead generation job aborted for icp={icp_id} (HTTP error)")
        except Exception:
            await db.rollback()
            logger.exception(f"Lead generation job failed for icp={icp_id}")
