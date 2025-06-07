"""Base revision for initial schema

Revision ID: a17d8c8efa28
Revises: c90352561e56
Create Date: 2025-06-06 23:14:38.664727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a17d8c8efa28'
down_revision: Union[str, None] = 'c90352561e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
