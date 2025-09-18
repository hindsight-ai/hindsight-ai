"""
Database engine and session management.

Builds the SQLAlchemy engine from environment configuration with sensible
test fallbacks (SQLite in-memory) and exposes FastAPI dependencies.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Database connection URL
# Generate dynamically from individual components if DATABASE_URL is not provided
def _get_database_url() -> str:
    # If DATABASE_URL is explicitly set, use it
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    # Otherwise, generate from individual components (all must be set)
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("POSTGRES_DB")

    if not all([db_user, db_password, db_host, db_port, db_name]):
        missing = []
        if not db_user: missing.append("POSTGRES_USER")
        if not db_password: missing.append("POSTGRES_PASSWORD")
        if not db_host: missing.append("POSTGRES_HOST")
        if not db_port: missing.append("POSTGRES_PORT")
        if not db_name: missing.append("POSTGRES_DB")
        raise ValueError(f"Missing required database environment variables: {', '.join(missing)}")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

DATABASE_URL = _get_database_url()

# Test override strategy:
# 1. If HINDSIGHT_TEST_DB is set, use it.
# 2. Else if TEST_DATABASE_URL (used by e2e tests) is set, use it (never override with sqlite).
# 3. Else if running under pytest (PYTEST_CURRENT_TEST) and not explicitly e2e (no E2E_TEST flag), force in-memory sqlite.
#    E2E tests spawn a real Postgres container and set TEST_DATABASE_URL; unit tests rely on fast sqlite.

explicit_test_db = os.getenv("HINDSIGHT_TEST_DB")
explicit_e2e_db = os.getenv("TEST_DATABASE_URL")  # set inside e2e fixtures
def _is_pytest_runtime() -> bool:
    """Best-effort detection that we're executing under pytest.

    Rationale: ``PYTEST_CURRENT_TEST`` is only set while an individual test is
    running, so module import time (e.g. when creating the engine) in CI may
    not yet have it. Detect presence of the pytest package in ``sys.modules``
    which is reliable once pytest has initialized collection. Also allow an
    override env ``PYTEST_RUNNING=1`` for explicit control if ever needed.
    """
    if os.getenv("PYTEST_RUNNING") == "1":  # explicit opt-in
        return True
    if "PYTEST_CURRENT_TEST" in os.environ:  # during an active test
        return True
    # During collection pytest is already imported
    if "pytest" in sys.modules:
        return True
    return False

pytest_indicator = _is_pytest_runtime()
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

def _create_engine_with_fallback(url: str, kwargs: dict):
    """Create engine; if creation fails under pytest and no explicit DB is set, fall back to in-memory sqlite.

    Note: Avoids an immediate connection ping so tests can patch create_engine easily
    without triggering real DB connections.
    """
    try:
        # Preserve exact call signature in tests when no kwargs provided
        _ce = getattr(sys.modules[__name__], "create_engine")
        eng = _ce(url, **kwargs) if kwargs else _ce(url)
        return eng
    except OperationalError:
        if _is_pytest_runtime() and not os.getenv("TEST_DATABASE_URL") and not os.getenv("HINDSIGHT_TEST_DB"):
            fallback_url = "sqlite+pysqlite:///:memory:"
            fk = {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
            _ce = getattr(sys.modules[__name__], "create_engine")
            return _ce(fallback_url, **fk)
        raise

# Create the SQLAlchemy engine (with fallback safety)
engine = _create_engine_with_fallback(DATABASE_URL, _sqlite_kwargs)

# When using an in-memory SQLite database we must create the schema eagerly so that
# each new connection (re-used via StaticPool) sees the tables. Some test modules
# call models.Base.metadata.create_all themselves, but many rely on implicit table
# availability via the dependency injection layer. Creating here avoids "no such table"
# OperationalError crashes for association tables like memory_block_keywords.
if DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL and not explicit_e2e_db and not explicit_test_db:
    try:  # pragma: no cover - simple safety wrapper
        from core.db import models  # local import to avoid circular import at module load
        models.Base.metadata.create_all(bind=engine)
    except Exception:  # pragma: no cover
        # Tests that explicitly manage schema can proceed; silent fail keeps behavior backwards compatible.
        pass

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Lazy one-time schema creation safeguard for SQLite test contexts where some
# test modules import the engine before creating tables. This complements the
# eager create_all executed for pure in-memory databases above but also covers
# file-based or fallback sqlite URLs used in certain integration tests.
_SCHEMA_INIT_DONE = False
def _ensure_sqlite_schema():  # pragma: no cover - simple guard logic
    global _SCHEMA_INIT_DONE
    if _SCHEMA_INIT_DONE:
        return
    url = str(engine.url)
    if url.startswith("sqlite"):
        try:
            from core.db import models
            models.Base.metadata.create_all(bind=engine)
            _SCHEMA_INIT_DONE = True
        except Exception:
            # Silently ignore; tests that manage schema explicitly will proceed.
            pass

def get_db():
    """Dependency to get a database session."""
    _ensure_sqlite_schema()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session_local():
    """Return a generator that yields a Session instance.

    Historically some test fixtures call `session = get_db_session_local()` and
    then `db = next(session)`. Returning a sessionmaker caused a
    TypeError: 'sessionmaker' object is not an iterator. To remain backward
    compatible with those fixtures, return a generator object that yields a
    Session and closes it when finished.
    """
    _ensure_sqlite_schema()

    def _session_gen():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return _session_gen()
