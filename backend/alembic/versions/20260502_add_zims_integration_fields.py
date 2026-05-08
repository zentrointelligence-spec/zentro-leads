"""add zims integration fields to zl_users

Revision ID: 20260502_add_zims_integration_fields
Revises: f1e2d3c4b5a6
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa

revision = "20260502zims"
down_revision = "b8c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column(
            "zl_users",
            sa.Column("zims_linked", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        )
    except Exception:
        pass  # Column already exists on fresh installs

    try:
        op.add_column(
            "zl_users",
            sa.Column("zims_agency_id", sa.String(), nullable=True),
        )
    except Exception:
        pass  # Column already exists on fresh installs

    try:
        op.add_column(
            "zl_users",
            sa.Column("zims_agent_id", sa.String(), nullable=True),
        )
    except Exception:
        pass  # Column already exists on fresh installs

    try:
        op.add_column(
            "zl_users",
            sa.Column("zims_api_url", sa.String(), nullable=True),
        )
    except Exception:
        pass  # Column already exists on fresh installs

    try:
        op.add_column(
            "zl_users",
            sa.Column("zims_api_key", sa.String(), nullable=True),
        )
    except Exception:
        pass  # Column already exists on fresh installs

    try:
        op.add_column(
            "zl_users",
            sa.Column("zims_last_sync_at", sa.DateTime(timezone=True), nullable=True),
        )
    except Exception:
        pass  # Column already exists on fresh installs

    try:
        op.add_column(
            "zl_users",
            sa.Column("zims_leads_pushed", sa.Integer(), nullable=True, server_default="0"),
        )
    except Exception:
        pass  # Column already exists on fresh installs


def downgrade() -> None:
    op.drop_column("zl_users", "zims_leads_pushed")
    op.drop_column("zl_users", "zims_last_sync_at")
    op.drop_column("zl_users", "zims_api_key")
    op.drop_column("zl_users", "zims_api_url")
    op.drop_column("zl_users", "zims_agent_id")
    op.drop_column("zl_users", "zims_agency_id")
    op.drop_column("zl_users", "zims_linked")
