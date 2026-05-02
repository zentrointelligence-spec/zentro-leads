"""add_enrichment_and_icp_fields

Revision ID: 4a2f9bcd1786
Revises: 20260501_add_conversion_tracking
Create Date: 2026-05-01 18:43:16.958506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a2f9bcd1786'
down_revision: Union[str, None] = '20260501_add_conversion_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ZLCompany enrichment fields
    op.add_column('zl_companies', sa.Column('ssm_verified', sa.Boolean(), nullable=True))
    op.add_column('zl_companies', sa.Column('years_in_business', sa.String(), nullable=True))

    # ZLLead ICP validation fields
    op.add_column('zl_leads', sa.Column('icp_match_score', sa.Integer(), nullable=True))
    op.add_column('zl_leads', sa.Column('icp_verdict', sa.String(), nullable=True))
    op.add_column('zl_leads', sa.Column('icp_reason', sa.Text(), nullable=True))
    op.add_column('zl_leads', sa.Column('recommended_product', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('zl_leads', 'recommended_product')
    op.drop_column('zl_leads', 'icp_reason')
    op.drop_column('zl_leads', 'icp_verdict')
    op.drop_column('zl_leads', 'icp_match_score')
    op.drop_column('zl_companies', 'years_in_business')
    op.drop_column('zl_companies', 'ssm_verified')
