"""Cascade memory block keywords when memory blocks are deleted

Revision ID: 2026050201
Revises: 2026050200
Create Date: 2026-05-02 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2026050201"
down_revision: Union[str, None] = "2026050200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("memory_block_keywords_memory_id_fkey", "memory_block_keywords", type_="foreignkey")
    op.create_foreign_key(
        "memory_block_keywords_memory_id_fkey",
        "memory_block_keywords",
        "memory_blocks",
        ["memory_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("memory_block_keywords_memory_id_fkey", "memory_block_keywords", type_="foreignkey")
    op.create_foreign_key(
        "memory_block_keywords_memory_id_fkey",
        "memory_block_keywords",
        "memory_blocks",
        ["memory_id"],
        ["id"],
    )
