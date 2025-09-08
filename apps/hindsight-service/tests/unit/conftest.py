import os
import pytest
from core.db.database import SessionLocal, engine
from core.db import models
from sqlalchemy.exc import OperationalError


@pytest.fixture(scope="session", autouse=True)
def create_schema_once():
    """Create all tables once per test session (SQLite in-memory resets per process)."""
    try:
        models.Base.metadata.create_all(bind=engine)
    except OperationalError as e:
        pytest.exit(f"Failed to create test schema: {e}")
    yield
    try:
        models.Base.metadata.drop_all(bind=engine)
    except Exception:
        pass

@pytest.fixture(autouse=True)
def clean_data():
    """Truncate all tables between tests without dropping metadata (faster)."""
    connection = engine.connect()
    trans = connection.begin()
    for table in reversed(models.Base.metadata.sorted_tables):
        connection.execute(table.delete())
    trans.commit()
    connection.close()
    yield

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
