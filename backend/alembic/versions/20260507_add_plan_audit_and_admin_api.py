"""Add plan audit columns to zl_users for admin API.

Adds plan_changed_at and plan_changed_by so admins can track who changed
a user's subscription plan and when.

Revision ID: 20260507admin
Revises: 20260507role
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260507admin"
down_revision: Union[str, None] = "20260507role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add plan_changed_at and plan_changed_by columns."""
    op.add_column(
        "zl_users",
        sa.Column("plan_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "zl_users",
        sa.Column("plan_changed_by", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove plan audit columns."""
    op.drop_column("zl_users", "plan_changed_by")
    op.drop_column("zl_users", "plan_changed_at")
