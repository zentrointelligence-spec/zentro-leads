#!/usr/bin/env python3
"""
Create the first Zentro admin account (or promote an existing user).

Run once after the initial deployment:

    ADMIN_EMAIL=admin@zentrointelligence.com \\
    ADMIN_PASSWORD=<strong-password> \\
    ADMIN_NAME="Zentro Admin" \\
    python scripts/create_admin.py

Environment variables:
    ADMIN_EMAIL     — email for the admin account  (default: admin@zentrointelligence.com)
    ADMIN_PASSWORD  — plaintext password           (required — script exits if unset)
    ADMIN_NAME      — display name                 (default: "Zentro Admin")
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.utils import hash_password
from app.config import settings
from app.models import ZLUser, PlanTier

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "admin@zentrointelligence.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_NAME     = os.getenv("ADMIN_NAME", "Zentro Admin")


async def create_admin() -> None:
    """Create or promote a user to the admin role."""
    if not ADMIN_PASSWORD:
        print("ERROR: ADMIN_PASSWORD env var is required. Set it before running.")
        sys.exit(1)

    engine = create_async_engine(settings.POSTGRES_URL_ASYNC, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        result = await db.execute(
            select(ZLUser).where(ZLUser.email == ADMIN_EMAIL.lower().strip())
        )
        existing: ZLUser | None = result.scalar_one_or_none()

        if existing:
            if existing.role == "admin":
                print(f"Admin '{ADMIN_EMAIL}' already exists — no changes made.")
            else:
                existing.role = "admin"
                await db.commit()
                print(f"User '{ADMIN_EMAIL}' promoted to admin role.")
            return

        admin = ZLUser(
            id=str(uuid.uuid4()),
            email=ADMIN_EMAIL.lower().strip(),
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name=ADMIN_NAME,
            agency_name="Zentro Intelligence",
            role="admin",
            plan=PlanTier.PRO,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        await db.commit()
        print(f"Admin account created: {ADMIN_EMAIL}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
