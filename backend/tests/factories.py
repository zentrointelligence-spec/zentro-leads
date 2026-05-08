"""
Direct DB factories — insert records without HTTP round-trips.

All factories call ``db.flush()`` so the inserted IDs are available
immediately within the same session. They do NOT commit, so all
records are cleaned up when the test's engine is disposed.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import hash_password
from app.models import (
    ZLICP,
    ZLCompany,
    ZLLead,
    ZLPerson,
    ZLPipelineStage,
    ZLUser,
    LeadStatus,
    LeadTier,
    PlanTier,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def make_user(
    db: AsyncSession,
    email: str = "factory@test.com",
    plan: str = "starter",
) -> ZLUser:
    """Create and flush a ZLUser."""
    user = ZLUser(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Factory User",
        company_name="Factory Agency Sdn Bhd",
        plan=PlanTier(plan),
        leads_limit=750,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def make_company(
    db: AsyncSession,
    name: str = "Acme Sdn Bhd",
    industry: str = "Manufacturing",
) -> ZLCompany:
    """Create and flush a ZLCompany."""
    company = ZLCompany(
        id=str(uuid.uuid4()),
        name=name,
        industry=industry,
        city="Kuala Lumpur",
        country="Malaysia",
        employee_count=50,
        employee_range="10-50",
        website="https://acme.com.my",
        domain="acme.com.my",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return company


async def make_person(
    db: AsyncSession,
    company_id: str | None = None,
    lead_type: str = "b2b",
    email: str = "ahmad@acme.com.my",
    job_title: str = "HR Manager",
    email_verified: bool = True,
) -> ZLPerson:
    """Create and flush a ZLPerson."""
    person = ZLPerson(
        id=str(uuid.uuid4()),
        company_id=company_id,
        full_name="Ahmad Hassan",
        job_title=job_title,
        email=email,
        email_verified=email_verified,
        email_confidence=0.95 if email_verified else 0.0,
        lead_type=lead_type,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(person)
    await db.flush()
    await db.refresh(person)
    return person


async def make_lead(
    db: AsyncSession,
    user_id: str,
    person_id: str | None = None,
    company_id: str | None = None,
    score: int = 75,
    tier: str = "warm",
    status: LeadStatus = LeadStatus.NEW,
    lead_type: str = "b2b",
) -> ZLLead:
    """Create and flush a ZLLead."""
    from app.models import LeadSource
    lead = ZLLead(
        id=str(uuid.uuid4()),
        user_id=user_id,
        person_id=person_id,
        company_id=company_id,
        lead_score=score,
        lead_tier=LeadTier(tier.lower()),
        status=status,
        lead_type=lead_type,
        insurance_type="group_medical",
        intent_signals=["hiring"],
        source=LeadSource.GOOGLE_MAPS,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return lead


async def make_icp(
    db: AsyncSession,
    user_id: str,
    name: str = "Manufacturing ICP",
) -> ZLICP:
    """Create and flush a ZLICP."""
    icp = ZLICP(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        description="Group medical insurance for manufacturing SMEs in KL",
        industries=["Manufacturing", "Food & Beverage"],
        job_titles=["HR Manager", "General Manager"],
        seniority_levels=["manager", "director"],
        company_sizes=["10-50", "50-200"],
        locations=["Kuala Lumpur", "Selangor"],
        keywords=["group medical", "employee benefits"],
        intent_signals=["hiring", "expansion"],
        search_queries=["HR manager manufacturing KL"],
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(icp)
    await db.flush()
    await db.refresh(icp)
    return icp


async def make_pipeline_entry(
    db: AsyncSession,
    user_id: str,
    lead_id: str,
    stage: str = "new",
) -> ZLPipelineStage:
    """Create and flush a ZLPipelineStage."""
    entry = ZLPipelineStage(
        id=str(uuid.uuid4()),
        user_id=user_id,
        lead_id=lead_id,
        stage=stage,
        created_at=_now(),
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry
