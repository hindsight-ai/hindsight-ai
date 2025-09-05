"""Add full-text search support for memory blocks

Revision ID: d65131155346
Revises: 456789012345
Create Date: 2025-09-01 00:20:57.543922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd65131155346'
down_revision: Union[str, None] = '456789012345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tsvector column for full-text search
    op.execute("ALTER TABLE memory_blocks ADD COLUMN search_vector tsvector;")
    
    # Add embedding column for future semantic search (nullable for now)
    op.add_column('memory_blocks', sa.Column('content_embedding', sa.TEXT, nullable=True))
    
    # Create function to update search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION update_search_vector()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', coalesce(NEW.content, '')), 'A') ||
                                setweight(to_tsvector('english', coalesce(NEW.lessons_learned, '')), 'B') ||
                                setweight(to_tsvector('english', coalesce(NEW.errors, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger to auto-update search vector
    op.execute("""
        CREATE TRIGGER update_search_vector_trigger
            BEFORE INSERT OR UPDATE ON memory_blocks
            FOR EACH ROW EXECUTE FUNCTION update_search_vector();
    """)
    
    # Update existing records with search vectors
    op.execute("""
        UPDATE memory_blocks SET 
            search_vector = setweight(to_tsvector('english', coalesce(content, '')), 'A') ||
                           setweight(to_tsvector('english', coalesce(lessons_learned, '')), 'B') ||
                           setweight(to_tsvector('english', coalesce(errors, '')), 'C')
        WHERE search_vector IS NULL;
    """)
    
    # Create GIN index for fast full-text search
    op.execute("CREATE INDEX idx_memory_blocks_search_vector ON memory_blocks USING GIN(search_vector);")
    
    # Create additional indexes for search performance
    op.create_index('idx_memory_blocks_content_gin', 'memory_blocks', [sa.text("to_tsvector('english', content)")], postgresql_using='gin')
    op.create_index('idx_memory_blocks_lessons_gin', 'memory_blocks', [sa.text("to_tsvector('english', lessons_learned)")], postgresql_using='gin')


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_memory_blocks_lessons_gin', table_name='memory_blocks')
    op.drop_index('idx_memory_blocks_content_gin', table_name='memory_blocks')
    op.execute("DROP INDEX IF EXISTS idx_memory_blocks_search_vector;")
    
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS update_search_vector_trigger ON memory_blocks;")
    op.execute("DROP FUNCTION IF EXISTS update_search_vector();")
    
    # Drop columns
    op.drop_column('memory_blocks', 'content_embedding')
    op.drop_column('memory_blocks', 'search_vector')
