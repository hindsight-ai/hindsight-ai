"""Initial schema creation

Revision ID: c90352561e56
Revises: 
Create Date: 2025-06-06 23:11:24.705200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c90352561e56'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables (pre-rename state)."""
    # agents
    op.create_table(
        'agents',
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('agent_name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # agent_transcripts
    op.create_table(
        'agent_transcripts',
        sa.Column('transcript_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.agent_id'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transcript_content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # memory_blocks (with memory_id before later rename)
    op.create_table(
        'memory_blocks',
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.agent_id'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('feedback_score', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # feedback_logs
    op.create_table(
        'feedback_logs',
        sa.Column('feedback_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('memory_blocks.memory_id'), nullable=False),
        sa.Column('feedback_type', sa.String(length=50), nullable=False),
        sa.Column('feedback_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # keywords
    op.create_table(
        'keywords',
        sa.Column('keyword_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('keyword_text', sa.String(length=255), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # memory_block_keywords
    op.create_table(
        'memory_block_keywords',
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('memory_blocks.memory_id'), primary_key=True, nullable=False),
        sa.Column('keyword_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('keywords.keyword_id'), primary_key=True, nullable=False),
    )


def downgrade() -> None:
    """Drop initial tables."""
    op.drop_table('memory_block_keywords')
    op.drop_table('keywords')
    op.drop_table('feedback_logs')
    op.drop_table('memory_blocks')
    op.drop_table('agent_transcripts')
    op.drop_table('agents')
