"""
Backfill scope fields for personal/organization rows where possible.

- memory_blocks: fill owner_user_id/org_id from related agents
- keywords: fill owner_user_id/org_id from associated memory blocks
- agents: fill owner_user_id/org_id from related memory blocks
- cleanup: clear owner/org on public rows

This is best-effort and conservative; rows that cannot be inferred remain.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'scopes_backfill_20240915'
down_revision = 'scopes_idx_20240915'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # memory_blocks: personal missing owner from agent
    op.execute(
        """
        UPDATE memory_blocks mb
        SET owner_user_id = a.owner_user_id
        FROM agents a
        WHERE mb.visibility_scope = 'personal'
          AND mb.owner_user_id IS NULL
          AND a.agent_id = mb.agent_id
          AND a.owner_user_id IS NOT NULL
        """
    )
    # memory_blocks: org missing org from agent
    op.execute(
        """
        UPDATE memory_blocks mb
        SET organization_id = a.organization_id
        FROM agents a
        WHERE mb.visibility_scope = 'organization'
          AND mb.organization_id IS NULL
          AND a.agent_id = mb.agent_id
          AND a.organization_id IS NOT NULL
        """
    )
    # memory_blocks: cleanup public owner/org
    op.execute(
        """
        UPDATE memory_blocks
        SET owner_user_id = NULL, organization_id = NULL
        WHERE visibility_scope = 'public' AND (owner_user_id IS NOT NULL OR organization_id IS NOT NULL)
        """
    )

    # keywords: personal missing owner from associated memory blocks
    op.execute(
        """
        UPDATE keywords k
        SET owner_user_id = sub.owner_user_id
        FROM (
            SELECT mbk.keyword_id, (array_agg(mb.owner_user_id))[1] AS owner_user_id
            FROM memory_block_keywords mbk
            JOIN memory_blocks mb ON mbk.memory_id = mb.id
            WHERE mb.visibility_scope = 'personal' AND mb.owner_user_id IS NOT NULL
            GROUP BY mbk.keyword_id
        ) AS sub
        WHERE k.keyword_id = sub.keyword_id
          AND k.visibility_scope = 'personal'
          AND k.owner_user_id IS NULL
        """
    )
    # keywords: org missing org from associated memory blocks
    op.execute(
        """
        UPDATE keywords k
        SET organization_id = sub.organization_id
        FROM (
            SELECT mbk.keyword_id, (array_agg(mb.organization_id))[1] AS organization_id
            FROM memory_block_keywords mbk
            JOIN memory_blocks mb ON mbk.memory_id = mb.id
            WHERE mb.visibility_scope = 'organization' AND mb.organization_id IS NOT NULL
            GROUP BY mbk.keyword_id
        ) AS sub
        WHERE k.keyword_id = sub.keyword_id
          AND k.visibility_scope = 'organization'
          AND k.organization_id IS NULL
        """
    )
    # keywords: cleanup public owner/org
    op.execute(
        """
        UPDATE keywords
        SET owner_user_id = NULL, organization_id = NULL
        WHERE visibility_scope = 'public' AND (owner_user_id IS NOT NULL OR organization_id IS NOT NULL)
        """
    )

    # agents: personal missing owner from related memory blocks
    op.execute(
        """
        UPDATE agents a
        SET owner_user_id = sub.owner_user_id
        FROM (
            SELECT agent_id, (array_agg(owner_user_id))[1] AS owner_user_id
            FROM memory_blocks
            WHERE visibility_scope = 'personal' AND owner_user_id IS NOT NULL
            GROUP BY agent_id
        ) AS sub
        WHERE a.agent_id = sub.agent_id
          AND a.visibility_scope = 'personal'
          AND a.owner_user_id IS NULL
        """
    )
    # agents: org missing org from related memory blocks
    op.execute(
        """
        UPDATE agents a
        SET organization_id = sub.organization_id
        FROM (
            SELECT agent_id, (array_agg(organization_id))[1] AS organization_id
            FROM memory_blocks
            WHERE visibility_scope = 'organization' AND organization_id IS NOT NULL
            GROUP BY agent_id
        ) AS sub
        WHERE a.agent_id = sub.agent_id
          AND a.visibility_scope = 'organization'
          AND a.organization_id IS NULL
        """
    )
    # agents: cleanup public owner/org
    op.execute(
        """
        UPDATE agents
        SET owner_user_id = NULL, organization_id = NULL
        WHERE visibility_scope = 'public' AND (owner_user_id IS NOT NULL OR organization_id IS NOT NULL)
        """
    )


def downgrade() -> None:
    # No-op; backfill is irreversible safely and intended for data hygiene only
    pass
