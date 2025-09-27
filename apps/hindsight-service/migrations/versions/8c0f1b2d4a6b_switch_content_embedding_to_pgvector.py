"""Switch content_embedding column to pgvector.

Revision ID: 8c0f1b2d4a6b
Revises: 6b3f2b7f1c23
Create Date: 2025-09-26 21:50:00.000000
"""

from alembic import op
import sqlalchemy as sa

try:  # pragma: no cover - optional dependency
    from pgvector.sqlalchemy import Vector  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Vector = None  # type: ignore

# revision identifiers, used by Alembic.
revision = "8c0f1b2d4a6b"
down_revision = "6b3f2b7f1c23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind else ""

    if dialect == "postgresql":
        extension_available = False
        chk = bind.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"))
        if chk.scalar():
            op.execute("CREATE EXTENSION IF NOT EXISTS vector")
            extension_available = True
        op.drop_column("memory_blocks", "content_embedding")
        if Vector is not None and extension_available:
            op.add_column(
                "memory_blocks",
                sa.Column("content_embedding", Vector(), nullable=True),
            )
        else:
            op.add_column(
                "memory_blocks",
                sa.Column("content_embedding", sa.dialects.postgresql.JSONB(), nullable=True),
            )
    else:
        op.drop_column("memory_blocks", "content_embedding")
        op.add_column("memory_blocks", sa.Column("content_embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind else ""

    op.drop_column("memory_blocks", "content_embedding")
    if dialect == "postgresql":
        op.add_column("memory_blocks", sa.Column("content_embedding", sa.Text(), nullable=True))
    else:
        op.add_column("memory_blocks", sa.Column("content_embedding", sa.Text(), nullable=True))
