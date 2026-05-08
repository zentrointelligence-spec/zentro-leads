"""add zl_pipeline_stages table

Revision ID: 20260506pipeline
Revises: 20260506social
Create Date: 2026-05-06

Creates the zl_pipeline_stages CRM table which tracks which stage
a lead is in for each user. A unique index ensures a lead can only
appear once per user pipeline.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260506pipeline"
down_revision = "20260506social"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zl_pipeline_stages",
        sa.Column("id",         sa.String(), nullable=False),
        sa.Column("user_id",    sa.String(), nullable=False),
        sa.Column("lead_id",    sa.String(), nullable=False),
        sa.Column("stage",      sa.String(), nullable=False),
        sa.Column("notes",      sa.Text(),   nullable=True),
        sa.Column("moved_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["zl_leads.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["zl_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_zl_pipeline_user_stage", "zl_pipeline_stages", ["user_id", "stage"])
    op.create_index("ix_zl_pipeline_user_lead",  "zl_pipeline_stages", ["user_id", "lead_id"], unique=True)
    op.create_index(op.f("ix_zl_pipeline_stages_lead_id"), "zl_pipeline_stages", ["lead_id"])
    op.create_index(op.f("ix_zl_pipeline_stages_user_id"), "zl_pipeline_stages", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_zl_pipeline_stages_user_id"), table_name="zl_pipeline_stages")
    op.drop_index(op.f("ix_zl_pipeline_stages_lead_id"), table_name="zl_pipeline_stages")
    op.drop_index("ix_zl_pipeline_user_lead",  table_name="zl_pipeline_stages")
    op.drop_index("ix_zl_pipeline_user_stage", table_name="zl_pipeline_stages")
    op.drop_table("zl_pipeline_stages")
