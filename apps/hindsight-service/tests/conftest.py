import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextvars import ContextVar
from testcontainers.postgres import PostgresContainer
from alembic import command
from alembic.config import Config

# Store original environment variables to restore after tests
_original_env = {}

def _setup_test_env():
    """Set up environment variables needed for database connection during tests"""
    global _original_env

    # Store original values
    test_vars = ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'DATABASE_URL']
    for var in test_vars:
        if var in os.environ:
            _original_env[var] = os.environ[var]

    # Only set test values if DATABASE_URL is not already set (to avoid conflicts with test containers)
    if not os.getenv("DATABASE_URL"):
        if not os.getenv("POSTGRES_USER"):
            os.environ["POSTGRES_USER"] = "testuser"
        if not os.getenv("POSTGRES_PASSWORD"):
            os.environ["POSTGRES_PASSWORD"] = "testpass"
        if not os.getenv("POSTGRES_HOST"):
            os.environ["POSTGRES_HOST"] = "localhost"
        if not os.getenv("POSTGRES_PORT"):
            os.environ["POSTGRES_PORT"] = "5432"
        if not os.getenv("POSTGRES_DB"):
            os.environ["POSTGRES_DB"] = "testdb"

def _restore_env():
    """Restore original environment variables after tests"""
    global _original_env

    # Remove test variables that weren't originally set
    test_vars = ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'DATABASE_URL']
    for var in test_vars:
        if var not in _original_env and var in os.environ:
            del os.environ[var]

    # Restore original values
    for var, value in _original_env.items():
        os.environ[var] = value

    _original_env.clear()

_setup_test_env()

@pytest.fixture(scope="session", autouse=True)
def _restore_test_env():
    """Restore original environment variables after all tests complete"""
    yield
    _restore_env()


@pytest.fixture(autouse=True)
def _beta_access_admin_env(monkeypatch):
    monkeypatch.setenv('BETA_ACCESS_ADMINS', 'ibarz.jean@gmail.com,dev@localhost')
    yield

# Session-wide Postgres test container
@pytest.fixture(scope="session")
def _test_postgres():
    image = os.getenv("TEST_POSTGRES_IMAGE", "postgres:16-alpine")
    with PostgresContainer(image) as pg:
        url = pg.get_connection_url()
        # Normalize driver to psycopg2 default used by app (remove +psycopg2 if present)
        if "+" in url:
            # e.g. postgresql+psycopg2:// -> postgresql://
            parts = url.split("+")
            url = parts[0] + "://" + parts[1].split("//",1)[1]
        os.environ["TEST_DATABASE_URL"] = url
        # Rebind core.db.database global engine/session if already imported (module import may have happened earlier)
        try:  # pragma: no cover - defensive
            import core.db.database as db_mod
            from sqlalchemy import create_engine as _ce
            new_engine = _ce(url, future=True)
            try:
                db_mod.engine.dispose()
            except Exception:
                pass
            db_mod.engine = new_engine
            db_mod.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)
        except Exception:
            pass
        yield url

# Apply Alembic migrations once
@pytest.fixture(scope="session", autouse=True)
def _migrated_db(_test_postgres):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _test_postgres)
    command.upgrade(cfg, "head")
    yield
    # Optional: command.downgrade(cfg, "base")

@pytest.fixture(scope="session")
def _engine(_test_postgres):
    return create_engine(_test_postgres, future=True)

@pytest.fixture(scope="session")
def _SessionLocal(_engine):
    return sessionmaker(bind=_engine, autoflush=False, autocommit=False)

_current_session: ContextVar[object] = ContextVar("_current_session", default=None)
# Fallback for threadpool contexts where ContextVar may not propagate
_GLOBAL_SESSION = None

# Per-test transactional session (fast cleanup without truncation)
@pytest.fixture(autouse=True)
def db_session(_engine, _SessionLocal):
    connection = _engine.connect()
    trans = connection.begin()
    session = _SessionLocal(bind=connection)
    token = _current_session.set(session)
    global _GLOBAL_SESSION
    _GLOBAL_SESSION = session
    try:
        yield session
    finally:
        _current_session.reset(token)
        _GLOBAL_SESSION = None
        try:
            trans.rollback()
        finally:
            session.close()
            connection.close()

# FastAPI dependency override so app endpoints use our transactional session
import core.db.database as db_module
from fastapi.testclient import TestClient
from core.api.main import app

def _override_get_db():
    # Prefer ContextVar-bound session
    session = _current_session.get()
    if session is not None:
        yield session
        return
    # Fall back to module-global when running inside threadpool where ContextVar may not propagate
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is not None:
        yield _GLOBAL_SESSION
        return
    # Last resort: ad-hoc session
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()

app.dependency_overrides[db_module.get_db] = _override_get_db

# Backwards compatibility: some integration tests expect a 'db' fixture name
@pytest.fixture
def db(db_session):
    return db_session

@pytest.fixture
def client():
    # Provide a default active scope header to tests to avoid many tests failing
    # with 'scope_required' when they don't set an explicit scope.
    return TestClient(app, headers={"X-Active-Scope": "personal"})
