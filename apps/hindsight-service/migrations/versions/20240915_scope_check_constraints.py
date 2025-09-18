"""
Add CHECK constraints to enforce scope field consistency.

Constraints:
- personal => owner_user_id IS NOT NULL
- organization => organization_id IS NOT NULL

Applied to: memory_blocks, keywords, agents
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'scopes_checks_20240915'
down_revision = 'scopes_backfill_20240915'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add constraints as NOT VALID to avoid failing existing data during upgrade.
    # They can be VALIDATEd later when data is clean.
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'ck_memory_blocks_personal_owner'
        ) THEN
            ALTER TABLE memory_blocks ADD CONSTRAINT ck_memory_blocks_personal_owner CHECK ((visibility_scope <> 'personal') OR (owner_user_id IS NOT NULL)) NOT VALID;
        END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'ck_memory_blocks_org_has_org'
        ) THEN
            ALTER TABLE memory_blocks ADD CONSTRAINT ck_memory_blocks_org_has_org CHECK ((visibility_scope <> 'organization') OR (organization_id IS NOT NULL)) NOT VALID;
        END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'ck_keywords_personal_owner'
        ) THEN
            ALTER TABLE keywords ADD CONSTRAINT ck_keywords_personal_owner CHECK ((visibility_scope <> 'personal') OR (owner_user_id IS NOT NULL)) NOT VALID;
        END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'ck_keywords_org_has_org'
        ) THEN
            ALTER TABLE keywords ADD CONSTRAINT ck_keywords_org_has_org CHECK ((visibility_scope <> 'organization') OR (organization_id IS NOT NULL)) NOT VALID;
        END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'ck_agents_personal_owner'
        ) THEN
            ALTER TABLE agents ADD CONSTRAINT ck_agents_personal_owner CHECK ((visibility_scope <> 'personal') OR (owner_user_id IS NOT NULL)) NOT VALID;
        END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'ck_agents_org_has_org'
        ) THEN
            ALTER TABLE agents ADD CONSTRAINT ck_agents_org_has_org CHECK ((visibility_scope <> 'organization') OR (organization_id IS NOT NULL)) NOT VALID;
        END IF;
    END
    $$;
    """)


def downgrade() -> None:
    # Drop constraints
    for table, names in (
        ('memory_blocks', ['ck_memory_blocks_personal_owner', 'ck_memory_blocks_org_has_org']),
        ('keywords', ['ck_keywords_personal_owner', 'ck_keywords_org_has_org']),
        ('agents', ['ck_agents_personal_owner', 'ck_agents_org_has_org']),
    ):
        for name in names:
            try:
                op.drop_constraint(name, table_name=table, type_='check')
            except Exception:
                pass
