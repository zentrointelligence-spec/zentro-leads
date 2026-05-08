"""Merge 20260507 market + admin branches into a single head.

Revision ID: 20260507merge2
Revises: 20260507market, 20260507admin
Create Date: 2026-05-07
"""
from typing import Sequence, Union

revision: str = "20260507merge2"
down_revision: Union[str, Sequence[str], None] = ("20260507market", "20260507admin")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
