"""
Add basic scope hardening constraints and indexes.

- Ensure visibility_scope is NOT NULL for key tables
- Add partial indexes to accelerate org-scoped queries

This migration intentionally avoids strict cross-field CHECK constraints (e.g.,
owner_user_id NOT NULL when personal) to prevent breaking existing data.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'scopes_idx_20240915'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill NULLs to 'personal' before enforcing NOT NULL
    op.execute("UPDATE memory_blocks SET visibility_scope = 'personal' WHERE visibility_scope IS NULL")
    op.execute("UPDATE keywords SET visibility_scope = 'personal' WHERE visibility_scope IS NULL")
    op.execute("UPDATE agents SET visibility_scope = 'personal' WHERE visibility_scope IS NULL")

    # Memory blocks: visibility_scope not null (defaults exist at model level)
    with op.batch_alter_table('memory_blocks') as batch:
        batch.alter_column('visibility_scope', existing_type=sa.String(length=20), nullable=False, server_default='personal')
    # Partial index for org-scope lookups
    op.execute("CREATE INDEX IF NOT EXISTS idx_memory_blocks_org_only ON memory_blocks (organization_id) WHERE visibility_scope = 'organization'")

    # Keywords: visibility_scope not null
    with op.batch_alter_table('keywords') as batch:
        batch.alter_column('visibility_scope', existing_type=sa.String(length=20), nullable=False, server_default='personal')
    op.execute("CREATE INDEX IF NOT EXISTS idx_keywords_org_only ON keywords (organization_id) WHERE visibility_scope = 'organization'")

    # Agents: visibility_scope not null
    with op.batch_alter_table('agents') as batch:
        batch.alter_column('visibility_scope', existing_type=sa.String(length=20), nullable=False, server_default='personal')
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_org_only ON agents (organization_id) WHERE visibility_scope = 'organization'")


def downgrade() -> None:
    # Drop partial indexes (safe no-ops if not exist)
    op.execute("DROP INDEX IF EXISTS idx_memory_blocks_org_only")
    op.execute("DROP INDEX IF EXISTS idx_keywords_org_only")
    op.execute("DROP INDEX IF EXISTS idx_agents_org_only")
    # Revert NOT NULLs (allow nulls)
    with op.batch_alter_table('memory_blocks') as batch:
        batch.alter_column('visibility_scope', existing_type=sa.String(length=20), nullable=True, server_default=None)
    with op.batch_alter_table('keywords') as batch:
        batch.alter_column('visibility_scope', existing_type=sa.String(length=20), nullable=True, server_default=None)
    with op.batch_alter_table('agents') as batch:
        batch.alter_column('visibility_scope', existing_type=sa.String(length=20), nullable=True, server_default=None)
