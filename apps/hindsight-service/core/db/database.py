import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Database connection URL
# This should ideally come from environment variables for production
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/hindsight_db")

# Test override strategy:
# 1. If HINDSIGHT_TEST_DB is set, use it.
# 2. Else if TEST_DATABASE_URL (used by e2e tests) is set, use it (never override with sqlite).
# 3. Else if running under pytest (PYTEST_CURRENT_TEST) and not explicitly e2e (no E2E_TEST flag), force in-memory sqlite.
#    E2E tests spawn a real Postgres container and set TEST_DATABASE_URL; unit tests rely on fast sqlite.

explicit_test_db = os.getenv("HINDSIGHT_TEST_DB")
explicit_e2e_db = os.getenv("TEST_DATABASE_URL")  # set inside e2e fixtures
pytest_indicator = "PYTEST_CURRENT_TEST" in os.environ
is_e2e_context = bool(explicit_e2e_db)

if explicit_test_db:
    DATABASE_URL = explicit_test_db
    _sqlite_kwargs = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
elif explicit_e2e_db:
    DATABASE_URL = explicit_e2e_db
    _sqlite_kwargs = {}
elif pytest_indicator and not is_e2e_context:
    # In-memory SQLite with StaticPool so the schema persists across connections
    DATABASE_URL = "sqlite+pysqlite:///:memory:"
    _sqlite_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
else:
    _sqlite_kwargs = {}

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, **_sqlite_kwargs)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session_local():
    """Return a sessionmaker factory (used by background worker threads)."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
