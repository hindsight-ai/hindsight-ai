"""Align metadata column in memory_blocks table

Revision ID: c90352561e56
Revises: 
Create Date: 2025-06-06 23:11:24.705200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c90352561e56'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('idx_agent_transcripts_agent_id'), table_name='agent_transcripts')
    op.drop_index(op.f('idx_agent_transcripts_conversation_id'), table_name='agent_transcripts')
    op.drop_index(op.f('idx_keywords_keyword_text'), table_name='keywords')
    op.drop_index(op.f('idx_memory_blocks_agent_id'), table_name='memory_blocks')
    op.drop_index(op.f('idx_memory_blocks_conversation_id'), table_name='memory_blocks')
    op.drop_index(op.f('idx_memory_blocks_timestamp'), table_name='memory_blocks')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('idx_memory_blocks_timestamp'), 'memory_blocks', ['timestamp'], unique=False)
    op.create_index(op.f('idx_memory_blocks_conversation_id'), 'memory_blocks', ['conversation_id'], unique=False)
    op.create_index(op.f('idx_memory_blocks_agent_id'), 'memory_blocks', ['agent_id'], unique=False)
    op.create_index(op.f('idx_keywords_keyword_text'), 'keywords', ['keyword_text'], unique=False)
    op.create_index(op.f('idx_agent_transcripts_conversation_id'), 'agent_transcripts', ['conversation_id'], unique=False)
    op.create_index(op.f('idx_agent_transcripts_agent_id'), 'agent_transcripts', ['agent_id'], unique=False)
    # ### end Alembic commands ###
