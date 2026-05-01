"""Add a partial unique index on users.external_subject.

`auth.get_or_create_user` binds a user row's external_subject on first
authenticated sign-in (TOFU). Without a uniqueness guarantee, two
concurrent first-time logins for the same email could both pass the
"existing_sub is NULL" branch, both write a value, and the loser's row
state would be overwritten silently — locking out one of them. We
enforce uniqueness in the DB so the second writer fails cleanly and the
first writer wins.

Use a partial index (WHERE external_subject IS NOT NULL) so legacy
rows with NULL external_subject keep working. Once the column is fully
populated (after every active user has signed in once post-fix), the
partial constraint can be tightened.

Revision ID: 2026042900
Revises: 8c0f1b2d4a6b
"""
from alembic import op


revision = "2026042900"
down_revision = "8c0f1b2d4a6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_external_subject
        ON users (external_subject)
        WHERE external_subject IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_external_subject")
