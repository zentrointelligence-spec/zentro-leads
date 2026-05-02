"""add_zl_auto_signals

Revision ID: b8c3d4e5f6a7
Revises: 4a2f9bcd1786
Create Date: 2026-05-02 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c3d4e5f6a7'
down_revision: Union[str, None] = '4a2f9bcd1786'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'zl_auto_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('company_id', sa.String(), nullable=True),
        sa.Column('lead_id', sa.String(), nullable=True),
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('signal_source', sa.String(), nullable=False),
        sa.Column('signal_type', sa.String(), nullable=False),
        sa.Column('signal_detail', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('why_now', sa.Text(), nullable=True),
        sa.Column('insurance_need', sa.String(), nullable=True),
        sa.Column('recommended_product', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('alerted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_zl_auto_signals_company', 'zl_auto_signals', ['company_id', 'signal_type'])
    op.create_index('ix_zl_auto_signals_user_detected', 'zl_auto_signals', ['user_id', 'detected_at'])
    op.create_index(op.f('ix_zl_auto_signals_company_id'), 'zl_auto_signals', ['company_id'], unique=False)
    op.create_index(op.f('ix_zl_auto_signals_lead_id'), 'zl_auto_signals', ['lead_id'], unique=False)
    op.create_index(op.f('ix_zl_auto_signals_signal_source'), 'zl_auto_signals', ['signal_source'], unique=False)
    op.create_index(op.f('ix_zl_auto_signals_signal_type'), 'zl_auto_signals', ['signal_type'], unique=False)
    op.create_index(op.f('ix_zl_auto_signals_user_id'), 'zl_auto_signals', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_zl_auto_signals_user_id'), table_name='zl_auto_signals')
    op.drop_index(op.f('ix_zl_auto_signals_signal_type'), table_name='zl_auto_signals')
    op.drop_index(op.f('ix_zl_auto_signals_signal_source'), table_name='zl_auto_signals')
    op.drop_index(op.f('ix_zl_auto_signals_lead_id'), table_name='zl_auto_signals')
    op.drop_index(op.f('ix_zl_auto_signals_company_id'), table_name='zl_auto_signals')
    op.drop_index('ix_zl_auto_signals_user_detected', table_name='zl_auto_signals')
    op.drop_index('ix_zl_auto_signals_company', table_name='zl_auto_signals')
    op.drop_table('zl_auto_signals')
