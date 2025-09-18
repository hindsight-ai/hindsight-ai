import pytest
from sqlalchemy.orm import Session
from core.db import models

# Permission / context fixtures

@pytest.fixture
def user_factory(db_session: Session):
    created = []
    def _create(email: str, is_superadmin: bool = False, display_name: str = None):
        user = models.User(email=email, display_name=display_name or email.split('@')[0], is_superadmin=is_superadmin)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        created.append(user)
        return user
    return _create

@pytest.fixture
def organization_factory(db_session: Session):
    created = []
    def _create(name: str):
        org = models.Organization(name=name)
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        created.append(org)
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

@pytest.fixture
def superadmin_context(user_factory):
    user = user_factory("superadmin@example.com", is_superadmin=True)
    return user

@pytest.fixture
def org_owner_context(user_factory, organization_factory, membership_factory):
    user = user_factory("owner@example.com")
    org = organization_factory("Test Org")
    membership_factory(org, user, role='owner', can_write=True)
    return user, org

@pytest.fixture
def editor_context(user_factory, organization_factory, membership_factory):
    user = user_factory("editor@example.com")
    org = organization_factory("Editor Org")
    membership_factory(org, user, role='editor', can_write=True)
    return user, org

@pytest.fixture
def viewer_context(user_factory, organization_factory, membership_factory):
    user = user_factory("viewer@example.com")
    org = organization_factory("Viewer Org")
    membership_factory(org, user, role='viewer', can_write=False)
    return user, org

# Compatibility fixtures for tests expecting older names
@pytest.fixture
def test_org_owner(org_owner_context):
    user, _ = org_owner_context
    return user

@pytest.fixture
def test_organization(org_owner_context):
    _, org = org_owner_context
    return org

@pytest.fixture
def test_user(user_factory):
    return user_factory("testuser@example.com")
