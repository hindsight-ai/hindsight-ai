"""Cascade feedback logs when memory blocks are deleted

Revision ID: 2026050200
Revises: 2026042900
Create Date: 2026-05-02 02:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2026050200"
down_revision: Union[str, None] = "2026042900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("feedback_logs_memory_id_fkey", "feedback_logs", type_="foreignkey")
    op.create_foreign_key(
        "feedback_logs_memory_id_fkey",
        "feedback_logs",
        "memory_blocks",
        ["memory_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("feedback_logs_memory_id_fkey", "feedback_logs", type_="foreignkey")
    op.create_foreign_key(
        "feedback_logs_memory_id_fkey",
        "feedback_logs",
        "memory_blocks",
        ["memory_id"],
        ["id"],
    )
