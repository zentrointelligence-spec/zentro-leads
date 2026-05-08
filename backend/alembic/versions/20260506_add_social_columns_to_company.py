"""add twitter_url and tiktok_url to zl_companies

Revision ID: 20260506social
Revises: 20260506leadstatus
Create Date: 2026-05-06

Adds twitter_url and tiktok_url VARCHAR columns to zl_companies.
linkedin_url already exists from the initial migration so it is
skipped here.

Each add_column is wrapped in a try/except so the migration is safe
to run against both fresh databases (column doesn't exist yet) and
existing databases that may have had these columns added manually.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260506social"
down_revision = "20260506leadstatus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add twitter_url and tiktok_url columns to zl_companies."""
    for col_name in ("twitter_url", "tiktok_url"):
        try:
            op.add_column(
                "zl_companies",
                sa.Column(col_name, sa.String(), nullable=True),
            )
        except Exception:
            # Column already exists — safe to continue
            pass


def downgrade() -> None:
    """Drop twitter_url and tiktok_url from zl_companies."""
    for col_name in ("tiktok_url", "twitter_url"):
        try:
            op.drop_column("zl_companies", col_name)
        except Exception:
            pass
