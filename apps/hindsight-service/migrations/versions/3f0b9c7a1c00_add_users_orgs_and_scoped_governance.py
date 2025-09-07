"""Add users/orgs tables and scoped governance columns + indexes

Revision ID: 3f0b9c7a1c00
Revises: 251ad5240261
Create Date: 2025-09-07 21:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3f0b9c7a1c00'
down_revision: Union[str, None] = '251ad5240261'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('display_name', sa.Text(), nullable=True),
        sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('auth_provider', sa.Text(), nullable=True),
        sa.Column('external_subject', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)

    # 2) Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('slug', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.UniqueConstraint('name', name='uq_organizations_name'),
        sa.UniqueConstraint('slug', name='uq_organizations_slug'),
    )

    # 3) Add governance columns to agents
    op.add_column('agents', sa.Column('visibility_scope', sa.Text(), nullable=False, server_default='personal'))
    op.add_column('agents', sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('agents', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_agents_owner_user_id', 'agents', 'users', ['owner_user_id'], ['id'])
    op.create_foreign_key('fk_agents_organization_id', 'agents', 'organizations', ['organization_id'], ['id'])
    # Check constraint for visibility_scope
    op.create_check_constraint('ck_agents_visibility_scope', 'agents', "visibility_scope in ('personal','organization','public')")
    # Drop global unique on agent_name (if present) and replace with scoped uniques
    try:
        op.drop_constraint('agents_agent_name_key', 'agents', type_='unique')
    except Exception:
        # In some DBs the constraint may be named differently or already absent
        pass
    op.create_index('idx_agents_owner_user_id', 'agents', ['owner_user_id'], unique=False)
    op.create_index('idx_agents_org_scope', 'agents', ['organization_id', 'visibility_scope'], unique=False)
    # Scoped unique indexes on lower(agent_name)
    op.create_index(
        'uq_agents_personal_lower_name',
        'agents',
        [sa.text('owner_user_id'), sa.text('lower(agent_name)')],
        unique=True,
        postgresql_where=sa.text("visibility_scope = 'personal'"),
    )
    op.create_index(
        'uq_agents_org_lower_name',
        'agents',
        [sa.text('organization_id'), sa.text('lower(agent_name)')],
        unique=True,
        postgresql_where=sa.text("visibility_scope = 'organization'"),
    )
    op.create_index(
        'uq_agents_public_lower_name',
        'agents',
        [sa.text('lower(agent_name)')],
        unique=True,
        postgresql_where=sa.text("visibility_scope = 'public'"),
    )

    # 4) Add governance columns to keywords
    op.add_column('keywords', sa.Column('visibility_scope', sa.Text(), nullable=False, server_default='personal'))
    op.add_column('keywords', sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('keywords', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_keywords_owner_user_id', 'keywords', 'users', ['owner_user_id'], ['id'])
    op.create_foreign_key('fk_keywords_organization_id', 'keywords', 'organizations', ['organization_id'], ['id'])
    op.create_check_constraint('ck_keywords_visibility_scope', 'keywords', "visibility_scope in ('personal','organization','public')")
    # Drop global unique on keyword_text and replace with scoped uniques
    try:
        op.drop_constraint('keywords_keyword_text_key', 'keywords', type_='unique')
    except Exception:
        pass
    op.create_index('idx_keywords_owner_user_id', 'keywords', ['owner_user_id'], unique=False)
    op.create_index('idx_keywords_org_scope', 'keywords', ['organization_id', 'visibility_scope'], unique=False)
    op.create_index(
        'uq_keywords_personal_lower_text',
        'keywords',
        [sa.text('owner_user_id'), sa.text('lower(keyword_text)')],
        unique=True,
        postgresql_where=sa.text("visibility_scope = 'personal'"),
    )
    op.create_index(
        'uq_keywords_org_lower_text',
        'keywords',
        [sa.text('organization_id'), sa.text('lower(keyword_text)')],
        unique=True,
        postgresql_where=sa.text("visibility_scope = 'organization'"),
    )
    op.create_index(
        'uq_keywords_public_lower_text',
        'keywords',
        [sa.text('lower(keyword_text)')],
        unique=True,
        postgresql_where=sa.text("visibility_scope = 'public'"),
    )

    # 5) Add governance columns to memory_blocks
    op.add_column('memory_blocks', sa.Column('visibility_scope', sa.Text(), nullable=False, server_default='personal'))
    op.add_column('memory_blocks', sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('memory_blocks', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_memory_blocks_owner_user_id', 'memory_blocks', 'users', ['owner_user_id'], ['id'])
    op.create_foreign_key('fk_memory_blocks_organization_id', 'memory_blocks', 'organizations', ['organization_id'], ['id'])
    op.create_check_constraint('ck_memory_blocks_visibility_scope', 'memory_blocks', "visibility_scope in ('personal','organization','public')")
    op.create_index('idx_memory_blocks_owner_user_id', 'memory_blocks', ['owner_user_id'], unique=False)
    op.create_index('idx_memory_blocks_org_scope', 'memory_blocks', ['organization_id', 'visibility_scope'], unique=False)

    # 6) Create organization_memberships
    op.create_table(
        'organization_memberships',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('can_read', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('can_write', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
    )
    op.create_index('idx_org_memberships_user_id', 'organization_memberships', ['user_id'], unique=False)
    op.create_check_constraint('ck_org_memberships_role', 'organization_memberships', "role in ('owner','admin','editor','viewer')")


def downgrade() -> None:
    # Drop organization_memberships
    op.drop_constraint('ck_org_memberships_role', 'organization_memberships', type_='check')
    op.drop_index('idx_org_memberships_user_id', table_name='organization_memberships')
    op.drop_table('organization_memberships')

    # Remove governance from memory_blocks
    op.drop_index('idx_memory_blocks_org_scope', table_name='memory_blocks')
    op.drop_index('idx_memory_blocks_owner_user_id', table_name='memory_blocks')
    op.drop_constraint('fk_memory_blocks_organization_id', 'memory_blocks', type_='foreignkey')
    op.drop_constraint('fk_memory_blocks_owner_user_id', 'memory_blocks', type_='foreignkey')
    op.drop_constraint('ck_memory_blocks_visibility_scope', 'memory_blocks', type_='check')
    op.drop_column('memory_blocks', 'organization_id')
    op.drop_column('memory_blocks', 'owner_user_id')
    op.drop_column('memory_blocks', 'visibility_scope')

    # Remove governance from keywords
    for idx in (
        'uq_keywords_public_lower_text',
        'uq_keywords_org_lower_text',
        'uq_keywords_personal_lower_text',
        'idx_keywords_org_scope',
        'idx_keywords_owner_user_id',
    ):
        try:
            op.drop_index(idx, table_name='keywords')
        except Exception:
            pass
    for fk in ('fk_keywords_organization_id', 'fk_keywords_owner_user_id'):
        try:
            op.drop_constraint(fk, 'keywords', type_='foreignkey')
        except Exception:
            pass
    try:
        op.drop_constraint('ck_keywords_visibility_scope', 'keywords', type_='check')
    except Exception:
        pass
    op.drop_column('keywords', 'organization_id')
    op.drop_column('keywords', 'owner_user_id')
    op.drop_column('keywords', 'visibility_scope')
    # Best effort: restore global unique
    try:
        op.create_unique_constraint('keywords_keyword_text_key', 'keywords', ['keyword_text'])
    except Exception:
        pass

    # Remove governance from agents
    for idx in (
        'uq_agents_public_lower_name',
        'uq_agents_org_lower_name',
        'uq_agents_personal_lower_name',
        'idx_agents_org_scope',
        'idx_agents_owner_user_id',
    ):
        try:
            op.drop_index(idx, table_name='agents')
        except Exception:
            pass
    for fk in ('fk_agents_organization_id', 'fk_agents_owner_user_id'):
        try:
            op.drop_constraint(fk, 'agents', type_='foreignkey')
        except Exception:
            pass
    try:
        op.drop_constraint('ck_agents_visibility_scope', 'agents', type_='check')
    except Exception:
        pass
    op.drop_column('agents', 'organization_id')
    op.drop_column('agents', 'owner_user_id')
    op.drop_column('agents', 'visibility_scope')
    # Best effort: restore global unique
    try:
        op.create_unique_constraint('agents_agent_name_key', 'agents', ['agent_name'])
    except Exception:
        pass

    # Drop organizations and users
    op.drop_table('organizations')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
