"""
Shared SQLAlchemy base and helpers.
"""
import uuid  # noqa: F401 - for default factories elsewhere
from sqlalchemy.orm import declarative_base
from datetime import datetime, UTC

# Import SQLite compilation shims for PostgreSQL-only types when running tests
# under SQLite. Keep import side-effect consistent with previous module layout.
try:  # pragma: no cover - defensive import
    from .. import sqlite_compiler_shims  # noqa: F401
except Exception:  # pragma: no cover
    pass


def now_utc():
    """Return an aware UTC datetime for default/updated timestamps."""
    return datetime.now(UTC)


Base = declarative_base()

