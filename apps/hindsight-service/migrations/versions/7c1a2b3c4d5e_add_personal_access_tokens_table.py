"""add personal access tokens table

Revision ID: 7c1a2b3c4d5e
Revises: 39b55ecbd958
Create Date: 2025-09-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7c1a2b3c4d5e'
down_revision: Union[str, None] = '39b55ecbd958'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'personal_access_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_id', sa.String(length=64), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('prefix', sa.String(length=12), nullable=True),
        sa.Column('last_four', sa.String(length=4), nullable=True),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_id', name='uq_pat_token_id'),
    )
    op.create_index('ix_pat_token_id', 'personal_access_tokens', ['token_id'], unique=True)
    op.create_index('idx_pat_user_created', 'personal_access_tokens', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_pat_status', 'personal_access_tokens', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_pat_status', table_name='personal_access_tokens')
    op.drop_index('idx_pat_user_created', table_name='personal_access_tokens')
    op.drop_index('ix_pat_token_id', table_name='personal_access_tokens')
    op.drop_table('personal_access_tokens')

