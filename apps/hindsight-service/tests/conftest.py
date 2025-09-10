import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextvars import ContextVar
from testcontainers.postgres import PostgresContainer
from alembic import command
from alembic.config import Config

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

# Per-test transactional session (fast cleanup without truncation)
@pytest.fixture(autouse=True)
def db_session(_engine, _SessionLocal):
    connection = _engine.connect()
    trans = connection.begin()
    session = _SessionLocal(bind=connection)
    token = _current_session.set(session)
    try:
        yield session
    finally:
        _current_session.reset(token)
        session.close()
        trans.rollback()
        connection.close()

# FastAPI dependency override so app endpoints use our transactional session
import core.db.database as db_module
from fastapi.testclient import TestClient
from core.api.main import app

def _override_get_db():
    session = _current_session.get()
    if session is None:  # Fallback: create ad-hoc session (should not normally happen inside tests)
        session = _SessionLocal()
        try:
            yield session
        finally:
            session.close()
    else:
        yield session

app.dependency_overrides[db_module.get_db] = _override_get_db

# Backwards compatibility: some integration tests expect a 'db' fixture name
@pytest.fixture
def db(db_session):
    return db_session

@pytest.fixture
def client():
    return TestClient(app)
