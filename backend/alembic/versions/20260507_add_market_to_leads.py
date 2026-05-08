"""Add market column to zl_leads.

Revision ID: 20260507market
Revises: 20260507b2c
Create Date: 2026-05-07
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260507market"
down_revision: Union[str, None] = "20260507b2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add market column to zl_leads with an index."""
    try:
        op.add_column(
            "zl_leads",
            sa.Column("market", sa.String(), nullable=True),
        )
    except Exception:
        pass  # idempotent — column already exists

    try:
        op.create_index("ix_zl_leads_market", "zl_leads", ["market"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("ix_zl_leads_market", table_name="zl_leads")
    except Exception:
        pass
    try:
        op.drop_column("zl_leads", "market")
    except Exception:
        pass
