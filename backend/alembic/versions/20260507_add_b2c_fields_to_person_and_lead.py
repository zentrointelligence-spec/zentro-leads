"""Add B2C fields to zl_people and zl_leads.

Adds B2C-specific demographic, life-event, and insurance fields to the
person table, plus lead_type and insurance_type classification columns
to both the people and leads tables.

Revision ID: 20260507b2c
Revises: 20260506merge
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260507b2c"
down_revision: Union[str, None] = "20260506merge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── zl_people — B2C fields ────────────────────────────────────
    new_people_cols = [
        ("lead_type",          sa.String(),                   "b2b"),
        ("age",                sa.Integer(),                   None),
        ("age_bracket",        sa.String(),                    None),
        ("income_bracket",     sa.String(),                    None),
        ("life_event",         sa.String(),                    None),
        ("life_event_date",    sa.DateTime(timezone=True),    None),
        ("life_event_source",  sa.String(),                    None),
        ("vehicle_type",       sa.String(),                    None),
        ("vehicle_model",      sa.String(),                    None),
        ("property_type",      sa.String(),                    None),
        ("insurance_need",     sa.String(),                    None),
    ]
    for col_name, col_type, server_default in new_people_cols:
        try:
            kwargs = {"nullable": True}
            if server_default is not None:
                kwargs["server_default"] = server_default
            op.add_column("zl_people", sa.Column(col_name, col_type, **kwargs))
        except Exception:
            pass  # Column already exists on fresh installs that ran earlier migrations

    # ── zl_leads — lead_type + insurance_type ─────────────────────
    for col_name, col_type, server_default in [
        ("lead_type",      sa.String(), "b2b"),
        ("insurance_type", sa.String(), None),
    ]:
        try:
            kwargs = {"nullable": True}
            if server_default is not None:
                kwargs["server_default"] = server_default
            op.add_column("zl_leads", sa.Column(col_name, col_type, **kwargs))
        except Exception:
            pass


def downgrade() -> None:
    for col in [
        "lead_type", "age", "age_bracket", "income_bracket", "life_event",
        "life_event_date", "life_event_source", "vehicle_type", "vehicle_model",
        "property_type", "insurance_need",
    ]:
        try:
            op.drop_column("zl_people", col)
        except Exception:
            pass

    for col in ["lead_type", "insurance_type"]:
        try:
            op.drop_column("zl_leads", col)
        except Exception:
            pass
