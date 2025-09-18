"""
Draft RLS policies for scoped tables (feature-flagged).

Enables row-level security and creates SELECT policies conditioned on a
custom GUC 'hindsight.enable_rls'. To enable RLS in a session:

  SET LOCAL hindsight.enable_rls = 'on';
  SET LOCAL hindsight.user_id = '<uuid>';
  SET LOCAL hindsight.org_id = '<uuid>';

This migration does not force RLS on; it conditionally enables and creates
policies only when the GUC is set. Administrators can set these GUCs at the
database/user level to enable RLS per environment.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'rls_policies_20240915'
down_revision = 'scopes_checks_20240915'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF current_setting('hindsight.enable_rls', true) = 'on' THEN
            -- Memory Blocks RLS
            ALTER TABLE memory_blocks ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS mb_select_public ON memory_blocks;
            DROP POLICY IF EXISTS mb_select_personal ON memory_blocks;
            DROP POLICY IF EXISTS mb_select_org ON memory_blocks;
            CREATE POLICY mb_select_public ON memory_blocks FOR SELECT USING (visibility_scope = 'public');
            CREATE POLICY mb_select_personal ON memory_blocks FOR SELECT USING (
              visibility_scope = 'personal' AND owner_user_id::text = current_setting('hindsight.user_id', true)
            );
            CREATE POLICY mb_select_org ON memory_blocks FOR SELECT USING (
              visibility_scope = 'organization' AND organization_id::text = current_setting('hindsight.org_id', true)
            );

            -- Keywords RLS
            ALTER TABLE keywords ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS kw_select_public ON keywords;
            DROP POLICY IF EXISTS kw_select_personal ON keywords;
            DROP POLICY IF EXISTS kw_select_org ON keywords;
            CREATE POLICY kw_select_public ON keywords FOR SELECT USING (visibility_scope = 'public');
            CREATE POLICY kw_select_personal ON keywords FOR SELECT USING (
              visibility_scope = 'personal' AND owner_user_id::text = current_setting('hindsight.user_id', true)
            );
            CREATE POLICY kw_select_org ON keywords FOR SELECT USING (
              visibility_scope = 'organization' AND organization_id::text = current_setting('hindsight.org_id', true)
            );

            -- Agents RLS
            ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS ag_select_public ON agents;
            DROP POLICY IF EXISTS ag_select_personal ON agents;
            DROP POLICY IF EXISTS ag_select_org ON agents;
            CREATE POLICY ag_select_public ON agents FOR SELECT USING (visibility_scope = 'public');
            CREATE POLICY ag_select_personal ON agents FOR SELECT USING (
              visibility_scope = 'personal' AND owner_user_id::text = current_setting('hindsight.user_id', true)
            );
            CREATE POLICY ag_select_org ON agents FOR SELECT USING (
              visibility_scope = 'organization' AND organization_id::text = current_setting('hindsight.org_id', true)
            );
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          -- Drop policies if exist
          DROP POLICY IF EXISTS mb_select_public ON memory_blocks;
          DROP POLICY IF EXISTS mb_select_personal ON memory_blocks;
          DROP POLICY IF EXISTS mb_select_org ON memory_blocks;
          ALTER TABLE memory_blocks DISABLE ROW LEVEL SECURITY;

          DROP POLICY IF EXISTS kw_select_public ON keywords;
          DROP POLICY IF EXISTS kw_select_personal ON keywords;
          DROP POLICY IF EXISTS kw_select_org ON keywords;
          ALTER TABLE keywords DISABLE ROW LEVEL SECURITY;

          DROP POLICY IF EXISTS ag_select_public ON agents;
          DROP POLICY IF EXISTS ag_select_personal ON agents;
          DROP POLICY IF EXISTS ag_select_org ON agents;
          ALTER TABLE agents DISABLE ROW LEVEL SECURITY;
        END
        $$;
        """
    )
