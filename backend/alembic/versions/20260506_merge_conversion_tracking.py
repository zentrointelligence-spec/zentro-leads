"""Merge conversion-tracking branch into main migration chain.

The 20260501_add_conversion_tracking migration branched off f1e2d3c4b5a6
while the main chain continued through b8c3d4e5f6a7 → 20260502zims → …
This merge migration combines both heads so `alembic upgrade head` works.

Revision ID: 20260506merge
Revises: 20260506pipeline, 20260501_add_conversion_tracking
Create Date: 2026-05-06
"""
from typing import Sequence, Union

revision: str = "20260506merge"
down_revision: Union[str, Sequence[str], None] = (
    "20260506pipeline",
    "20260501_add_conversion_tracking",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema changes — merge commit only."""
    pass


def downgrade() -> None:
    """No schema changes — merge commit only."""
    pass
