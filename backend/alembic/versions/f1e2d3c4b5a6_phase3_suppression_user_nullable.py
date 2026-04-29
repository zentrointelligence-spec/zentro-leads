"""phase3 — allow global suppression rows (nullable user_id)

Revision ID: f1e2d3c4b5a6
Revises: 62069b40a737
Create Date: 2026-04-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, None] = "62069b40a737"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "zl_suppression_list",
        "user_id",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "zl_suppression_list",
        "user_id",
        existing_type=sa.String(),
        nullable=False,
    )
