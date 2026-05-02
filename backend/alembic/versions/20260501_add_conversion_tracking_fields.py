"""add_conversion_tracking_fields

Revision ID: 20260501_add_conversion_tracking
Revises: f1e2d3c4b5a6
Create Date: 2026-05-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260501_add_conversion_tracking"
down_revision: Union[str, None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to zl_scoring_feedback
    op.add_column("zl_scoring_feedback", sa.Column("event_type", sa.String(), nullable=True))
    op.add_column("zl_scoring_feedback", sa.Column("icp_id", sa.String(), sa.ForeignKey("zl_icps.id"), nullable=True))
    op.add_column("zl_scoring_feedback", sa.Column("intent_signals", sa.JSON(), nullable=True))
    op.add_column("zl_scoring_feedback", sa.Column("channel", sa.String(), nullable=True))
    op.add_column("zl_scoring_feedback", sa.Column("days_to_reply", sa.Integer(), nullable=True))
    op.add_column("zl_scoring_feedback", sa.Column("revenue_value", sa.Float(), nullable=True))

    # Make existing columns nullable for event tracking flexibility
    op.alter_column("zl_scoring_feedback", "original_score", existing_type=sa.Integer(), nullable=True)
    op.alter_column("zl_scoring_feedback", "original_breakdown", existing_type=sa.JSON(), nullable=True)

    # Create index on event_type
    op.create_index("ix_zl_scoring_feedback_event_type", "zl_scoring_feedback", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_zl_scoring_feedback_event_type", table_name="zl_scoring_feedback")
    op.drop_column("zl_scoring_feedback", "revenue_value")
    op.drop_column("zl_scoring_feedback", "days_to_reply")
    op.drop_column("zl_scoring_feedback", "channel")
    op.drop_column("zl_scoring_feedback", "intent_signals")
    op.drop_column("zl_scoring_feedback", "icp_id")
    op.drop_column("zl_scoring_feedback", "event_type")
    op.alter_column("zl_scoring_feedback", "original_score", existing_type=sa.Integer(), nullable=False)
    op.alter_column("zl_scoring_feedback", "original_breakdown", existing_type=sa.JSON(), nullable=False)
