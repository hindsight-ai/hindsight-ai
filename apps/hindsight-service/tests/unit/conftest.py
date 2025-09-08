import pytest
from core.db.database import SessionLocal, engine
from core.db import models

# Create all tables once at import (cleaned per-test below)
models.Base.metadata.create_all(bind=engine)

@pytest.fixture(autouse=True)
def clean_schema():
    """Full isolation: drop & recreate all tables per test.

    NOTE: This is heavier than truncation; keep only if test count small.
    """
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    # Could collect coverage or perform per-test finalization here if needed.

@pytest.fixture
def db_session():
    """Provide a SQLAlchemy session that always rolls back & closes.

    Prevents connection leakage and hanging subsequent tests waiting on pool.
    """
    db = SessionLocal()
    try:
        yield db
        # Optional explicit rollback to ensure no open transaction
        db.rollback()
    finally:
        db.close()
