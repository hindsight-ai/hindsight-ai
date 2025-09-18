import os
import uuid
import pytest
from core.db.database import SessionLocal, engine
from core.db import models
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


@pytest.fixture(scope="session", autouse=True)
def create_schema_once():
    """Create all tables once per test session (SQLite in-memory resets per process)."""
    try:
        models.Base.metadata.create_all(bind=engine)
    except OperationalError as e:
        # Retry once: engine may have fallen back inside database module; attempt again
        try:
            models.Base.metadata.create_all(bind=engine)
        except Exception:
            pytest.exit(f"Failed to create test schema after retry: {e}")
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

@pytest.fixture
def user_factory(db_session: Session):
    def _create(email: str, is_superadmin: bool = False, display_name: str = None):
        user = models.User(email=email, display_name=display_name or email.split('@')[0], is_superadmin=is_superadmin)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _create

@pytest.fixture
def organization_factory(db_session: Session):
    def _create(name: str):
        org = models.Organization(name=name)
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        return org
    return _create

@pytest.fixture
def membership_factory(db_session: Session):
    def _create(org, user, role: str = 'owner', can_read: bool = True, can_write: bool = True):
        m = models.OrganizationMembership(organization_id=org.id, user_id=user.id, role=role, can_read=can_read, can_write=can_write)
        db_session.add(m)
        db_session.commit()
        return m
    return _create
