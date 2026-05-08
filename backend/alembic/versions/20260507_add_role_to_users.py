"""Add role column to zl_users.

Adds a VARCHAR role column (default 'agent') to support role-based
access control: agent | owner | admin.

Revision ID: 20260507role
Revises: 20260507b2c
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260507role"
down_revision: Union[str, None] = "20260507b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role column with default 'agent'; backfill all existing rows."""
    op.add_column(
        "zl_users",
        sa.Column(
            "role",
            sa.String(),
            nullable=False,
            server_default="agent",
        ),
    )


def downgrade() -> None:
    """Remove role column."""
    op.drop_column("zl_users", "role")
