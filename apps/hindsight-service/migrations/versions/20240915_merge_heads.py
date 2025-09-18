"""
Merge heads created by parallel development branches.

This creates a new linear head by merging the following heads:
 - rls_policies_20240915
 - 7c1a2b3c4d5e

No schema changes are applied in this merge migration.
"""

from typing import Sequence, Union

# Alembic revision identifiers
revision: str = '20240915_merge_heads'
down_revision: Union[str, tuple[str, ...], None] = (
    'rls_policies_20240915',
    '7c1a2b3c4d5e',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge only; no operations required
    pass


def downgrade() -> None:
    # Merge only; no operations required
    pass
