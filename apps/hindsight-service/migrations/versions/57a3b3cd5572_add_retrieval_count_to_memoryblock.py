"""Add retrieval_count to MemoryBlock

Revision ID: 57a3b3cd5572
Revises: 14cd01c502f8
Create Date: 2025-06-07 17:26:52.560960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57a3b3cd5572'
down_revision: Union[str, None] = '14cd01c502f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('memory_blocks', sa.Column('retrieval_count', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('memory_blocks', 'retrieval_count')
    # ### end Alembic commands ###
