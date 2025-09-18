"""Add review token support to beta access requests

Revision ID: 6b3f2b7f1c23
Revises: 58d9df7d9301
Create Date: 2025-09-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime, timedelta, timezone

# revision identifiers, used by Alembic.
revision = '6b3f2b7f1c23'
down_revision = '58d9df7d9301'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('beta_access_requests', sa.Column('review_token', sa.String(), nullable=True))
    op.add_column('beta_access_requests', sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint('uq_beta_access_requests_review_token', 'beta_access_requests', ['review_token'])

    conn = op.get_bind()
    pending_requests = conn.execute(sa.text("SELECT id FROM beta_access_requests WHERE status = 'pending'")).fetchall()
    now = datetime.now(timezone.utc)
    for row in pending_requests:
        token = uuid.uuid4().hex + uuid.uuid4().hex
        expires_at = now + timedelta(days=7)
        conn.execute(
            sa.text(
                "UPDATE beta_access_requests SET review_token = :token, token_expires_at = :expires_at WHERE id = :request_id"
            ),
            {
                "token": token,
                "expires_at": expires_at,
                "request_id": row.id,
            },
        )


def downgrade():
    op.drop_constraint('uq_beta_access_requests_review_token', 'beta_access_requests', type_='unique')
    op.drop_column('beta_access_requests', 'token_expires_at')
    op.drop_column('beta_access_requests', 'review_token')
