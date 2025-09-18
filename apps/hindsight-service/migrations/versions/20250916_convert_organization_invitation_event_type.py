"""Convert legacy event_type 'organization_invitation' to 'org_invitation'

Revision ID: 20250916_convert_org_inv
Revises: 20240915_merge_heads
Create Date: 2025-09-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250916_convert_org_inv'
down_revision = '20240915_merge_heads'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Update notifications
    conn.execute(
        sa.text("""
        UPDATE notifications
        SET event_type = 'org_invitation'
        WHERE event_type = 'organization_invitation'
        """)
    )

    # Update email logs
    conn.execute(
        sa.text("""
        UPDATE email_notification_logs
        SET event_type = 'org_invitation'
        WHERE event_type = 'organization_invitation'
        """)
    )

    # Update user preferences
    conn.execute(
        sa.text("""
        UPDATE user_notification_preferences
        SET event_type = 'org_invitation'
        WHERE event_type = 'organization_invitation'
        """)
    )


def downgrade():
    conn = op.get_bind()
    # Revert notifications
    conn.execute(
        sa.text("""
        UPDATE notifications
        SET event_type = 'organization_invitation'
        WHERE event_type = 'org_invitation'
        """)
    )

    # Revert email logs
    conn.execute(
        sa.text("""
        UPDATE email_notification_logs
        SET event_type = 'organization_invitation'
        WHERE event_type = 'org_invitation'
        """)
    )

    # Revert user preferences
    conn.execute(
        sa.text("""
        UPDATE user_notification_preferences
        SET event_type = 'organization_invitation'
        WHERE event_type = 'org_invitation'
        """)
    )
