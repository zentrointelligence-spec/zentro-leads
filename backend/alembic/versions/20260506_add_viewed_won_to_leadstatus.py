"""add VIEWED and WON to leadstatus enum

Revision ID: 20260506leadstatus
Revises: 20260502zims
Create Date: 2026-05-06

PostgreSQL does not support removing values from an enum, but adding
new values with ALTER TYPE ... ADD VALUE is safe and transactional
(PostgreSQL 12+). We add VIEWED and WON without touching existing rows.
"""

from alembic import op

revision = "20260506leadstatus"
down_revision = "20260502zims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add VIEWED and WON to the leadstatus enum in PostgreSQL."""
    # ALTER TYPE ... ADD VALUE is DDL — must run outside a transaction block.
    # Alembic's op.execute handles this; we use IF NOT EXISTS (PG 9.6+) to
    # make the migration idempotent on environments that already have these values.
    op.execute("ALTER TYPE leadstatus ADD VALUE IF NOT EXISTS 'VIEWED' AFTER 'NEW'")
    op.execute("ALTER TYPE leadstatus ADD VALUE IF NOT EXISTS 'WON' AFTER 'CLOSED'")


def downgrade() -> None:
    """
    PostgreSQL does not support dropping enum values without recreating the type.
    This downgrade is intentionally a no-op to keep the migration safe.
    To fully revert: recreate the type and cast all affected rows manually.
    """
    pass
