"""fix_search_vector_column_type

Revision ID: 251ad5240261
Revises: d65131155346
Create Date: 2025-09-01 00:47:50.590390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '251ad5240261'
down_revision: Union[str, None] = 'd65131155346'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix search_vector column type to be proper tsvector."""
    # Check if the column is already tsvector type, if not convert it
    op.execute("""
        DO $$
        BEGIN
            -- Check if column exists and is not tsvector type
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'memory_blocks' 
                AND column_name = 'search_vector' 
                AND data_type != 'tsvector'
            ) THEN
                -- Drop the index before altering column type
                DROP INDEX IF EXISTS idx_memory_blocks_search_vector;
                
                -- Convert the column to tsvector type
                -- Since it contains text representation of tsvector, convert via text
                ALTER TABLE memory_blocks ALTER COLUMN search_vector TYPE tsvector USING search_vector::text::tsvector;
                
                -- Recreate the index
                CREATE INDEX idx_memory_blocks_search_vector ON memory_blocks USING GIN(search_vector);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    """Revert search_vector column type back to text.

    Ensure we drop the GIN index on search_vector prior to changing type, as
    text has no default operator class for GIN.
    """
    op.execute("DROP INDEX IF EXISTS idx_memory_blocks_search_vector;")
    op.execute("ALTER TABLE memory_blocks ALTER COLUMN search_vector TYPE text USING search_vector::text")
