#!/usr/bin/env python3
"""
DB integration test for Tender Monitor.
Creates a simulated tender match and verifies lead creation/upgrading.
Run: python scripts/test_tender_monitor_db.py
"""

import asyncio
import sys
sys.path.insert(0, "/home/sammy1998/zentro-leads/backend")

from datetime import datetime, timezone

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import (
    LeadSource,
    LeadStatus,
    LeadTier,
    ZLCompany,
    ZLICP,
    ZLLead,
    ZLPerson,
    ZLUser,
)
from app.jobs.tender_monitor import (
    _find_company_by_name,
    _find_existing_lead,
    _create_synthetic_person,
    _create_tender_lead,
    _upgrade_lead_to_hot,
)


async def test_db_operations():
    print("=" * 60)
    print("DB Integration Test: Tender Monitor")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Find or create test user
            result = await db.execute(
                select(ZLUser).where(ZLUser.email == "test_tender@leadradar.my")
            )
            user = result.scalar_one_or_none()
            if not user:
                user = ZLUser(
                    email="test_tender@leadradar.my",
                    hashed_password="test",
                    full_name="Test Tender User",
                    phone="+60123456789",
                    leads_limit=100,
                    leads_used_this_month=0,
                )
                db.add(user)
                await db.flush()
                print(f"Created test user: {user.id}")
            else:
                print(f"Found test user: {user.id}")

            # 2. Create test ICP
            icp = ZLICP(
                user_id=user.id,
                name="Test Construction ICP",
                description="Construction and logistics companies in Malaysia",
                industries=["construction", "logistics"],
                locations=["Kuala Lumpur", "Selangor"],
            )
            db.add(icp)
            await db.flush()
            print(f"Created test ICP: {icp.id}")

            # 3. Test: Create new company + lead from tender
            article = {
                "source": "fmt_business",
                "title": "Mega Builders Sdn Bhd wins RM200m highway contract",
                "description": "The company was awarded the project by the government.",
                "url": "https://example.com/news/1",
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

            company_name = "Mega Builders Sdn Bhd"

            # Find company (should not exist)
            company = await _find_company_by_name(db, company_name)
            if company:
                print(f"Company already exists: {company.name}")
            else:
                company = ZLCompany(
                    name=company_name,
                    industry="Construction",
                    country="Malaysia",
                    city="Kuala Lumpur",
                    data_source=LeadSource.NEWS,
                )
                db.add(company)
                await db.flush()
                print(f"Created company: {company.name} ({company.id})")

            # Create synthetic person
            person = await _create_synthetic_person(db, company.id, company.name)
            print(f"Created person: {person.full_name} ({person.id})")

            # Create tender lead
            lead = await _create_tender_lead(
                db, user.id, icp.id, company.id, person.id, article
            )
            print(f"Created lead: score={lead.lead_score}, tier={lead.lead_tier.value}, id={lead.id}")
            assert lead.lead_score == 85
            assert lead.lead_tier == LeadTier.HOT
            assert "tender_win" in lead.intent_signals
            print("  ✓ Lead score is 85")
            print("  ✓ Lead tier is HOT")
            print("  ✓ Intent signals include 'tender_win'")

            # 4. Test: Upgrade existing lead
            article2 = {
                "source": "businesstoday_my",
                "title": "Mega Builders Sdn Bhd secures second warehouse project",
                "description": "Additional contract worth RM50m.",
                "url": "https://example.com/news/2",
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

            # Lower the score first to simulate a warm lead
            lead.lead_score = 60
            lead.lead_tier = LeadTier.WARM
            await db.flush()

            await _upgrade_lead_to_hot(db, lead, article2)
            print(f"Upgraded lead: score={lead.lead_score}, tier={lead.lead_tier.value}")
            assert lead.lead_score == 85
            assert lead.lead_tier == LeadTier.HOT
            assert "tender_win" in lead.intent_signals
            print("  ✓ Lead upgraded from 60 to 85")
            print("  ✓ Tier upgraded to HOT")

            # 5. Test: Find existing lead
            found_lead = await _find_existing_lead(db, user.id, company.id)
            assert found_lead is not None
            assert found_lead.id == lead.id
            print("  ✓ Found existing lead by user+company")

            # 6. Cleanup
            await db.execute(
                select(ZLLead).where(ZLLead.id == lead.id)
            )
            await db.delete(lead)
            await db.delete(person)
            await db.delete(company)
            await db.delete(icp)
            await db.delete(user)
            await db.commit()
            print("\nCleanup complete — test records removed")

            print("\n🎉 All DB integration tests passed!")
            return True

        except Exception as exc:
            await db.rollback()
            print(f"\n❌ DB test failed: {exc}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    exit_code = 0 if asyncio.run(test_db_operations()) else 1
    sys.exit(exit_code)
