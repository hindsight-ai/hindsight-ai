"""add bulk operations table

Revision ID: 85f1accd00c7
Revises: 5bfbd21a9d4d
Create Date: 2025-09-08 20:48:04.664253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '85f1accd00c7'
down_revision: Union[str, None] = '5bfbd21a9d4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'bulk_operations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('request_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Text(), sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')"), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('finished_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('error_log', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bulk_operations_organization_id_created_at'), 'bulk_operations', ['organization_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_bulk_operations_actor_user_id_created_at'), 'bulk_operations', ['actor_user_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_bulk_operations_actor_user_id_created_at'), table_name='bulk_operations')
    op.drop_index(op.f('ix_bulk_operations_organization_id_created_at'), table_name='bulk_operations')
    op.drop_table('bulk_operations')
