import uuid
import pytest
from fastapi.testclient import TestClient
from core.api.main import app
from core.db.database import SessionLocal, engine
from core.db import models, crud, schemas

@pytest.fixture(scope="module")
def db():
    models.Base.metadata.create_all(bind=engine)
    try:
        yield SessionLocal()
    finally:
        models.Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def clean(db):
    for t in reversed(models.Base.metadata.sorted_tables):
        db.execute(t.delete())
    db.commit()
    yield

@pytest.fixture
def client(db):
    # Ensure app uses the same transactional session as test via dependency override
    import core.db.database as db_module
    original = app.dependency_overrides.get(db_module.get_db)

    def _override():
        yield db

    app.dependency_overrides[db_module.get_db] = _override
    try:
        yield TestClient(app)
    finally:
        # Restore any existing override to avoid bleed across tests
        if original is not None:
            app.dependency_overrides[db_module.get_db] = original
        else:
            app.dependency_overrides.pop(db_module.get_db, None)

@pytest.fixture
def org_with_user(db):
    user = models.User(email="planner@example.com", display_name="planner", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)
    org = models.Organization(name="PlanOrg", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)
    mem = models.OrganizationMembership(organization_id=org.id, user_id=user.id, role='owner', can_read=True, can_write=True)
    db.add(mem); db.commit()
    return user, org


def _h(u):
    name = u.email.split('@')[0]
    return {"x-auth-request-user": name, "x-auth-request-email": u.email}


def test_bulk_move_validation_errors(client, org_with_user):
    user, org = org_with_user
    # neither destination provided
    r = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json={}, headers=_h(user))
    assert r.status_code == 422
    # both destinations
    r = client.post(
        f"/bulk-operations/organizations/{org.id}/bulk-move",
        json={"destination_organization_id": str(uuid.uuid4()), "destination_owner_user_id": str(uuid.uuid4())},
        headers=_h(user),
    )
    assert r.status_code == 422


def test_bulk_move_conflict_detection(client, org_with_user, db):
    from unittest.mock import patch
    user, org = org_with_user
    dest = models.Organization(name="DestPlan", created_by=user.id)
    db.add(dest); db.commit(); db.refresh(dest)
    mem = models.OrganizationMembership(organization_id=dest.id, user_id=user.id, role='owner', can_read=True, can_write=True)
    db.add(mem); db.commit()
    crud.create_agent(db, schemas.AgentCreate(agent_name="dup", visibility_scope="organization", organization_id=org.id))
    crud.create_agent(db, schemas.AgentCreate(agent_name="dup", visibility_scope="organization", organization_id=dest.id))
    
    # Mock get_current_user_context to return user with correct memberships
    fake_user = user
    fake_memberships = [
        {"organization_id": str(org.id), "role": "owner", "can_read": True, "can_write": True},
        {"organization_id": str(dest.id), "role": "owner", "can_read": True, "can_write": True}
    ]
    fake_current_user = {
        "id": user.id,
        "is_superadmin": False,
        "memberships": fake_memberships,
        "memberships_by_org": {str(org.id): fake_memberships[0], str(dest.id): fake_memberships[1]},
    }
    
    with patch('core.api.bulk_operations._require_current_user', return_value=(fake_user, fake_current_user)):
        r = client.post(
            f"/bulk-operations/organizations/{org.id}/bulk-move",
            json={"destination_organization_id": str(dest.id), "resource_types": ["agents"]},
            headers=_h(user),
        )
    assert r.status_code == 200
    data = r.json()
    assert data["conflicts"]["agents"]
    assert data["resources_to_move"]["agents"] == 1


def test_bulk_delete_dry_run_counts(client, org_with_user, db):
    from unittest.mock import patch
    user, org = org_with_user
    # escalate to superadmin to ensure manage permission for delete planning
    user.is_superadmin = True
    db.commit(); db.refresh(user)
    crud.create_agent(db, schemas.AgentCreate(agent_name="a1", visibility_scope="organization", organization_id=org.id))
    crud.create_keyword(db, schemas.KeywordCreate(keyword_text="k1", visibility_scope="organization", organization_id=org.id))
    agent = crud.create_agent(db, schemas.AgentCreate(agent_name="mbagent", visibility_scope="organization", organization_id=org.id))
    crud.create_memory_block(db, schemas.MemoryBlockCreate(content="m1", visibility_scope="organization", organization_id=org.id, agent_id=agent.agent_id, conversation_id=uuid.uuid4()))
    
    # Mock get_current_user_context to return superadmin user
    fake_user = user
    fake_current_user = {
        "id": user.id,
        "is_superadmin": True,
        "memberships": [],
        "memberships_by_org": {},
    }
    
    with patch('core.api.bulk_operations._require_current_user', return_value=(fake_user, fake_current_user)):
        r = client.post(
            f"/bulk-operations/organizations/{org.id}/bulk-delete",
            json={"dry_run": True},
            headers=_h(user),
        )
    assert r.status_code == 200
    data = r.json()
    # Two agents were created (a1 and mbagent)
    assert data["resources_to_delete"]["agents"] == 2
    assert data["resources_to_delete"]["keywords"] == 1
    assert data["resources_to_delete"]["memory_blocks"] == 1


def test_bulk_move_forbidden_destination(client, org_with_user, db):
    user, org = org_with_user
    dest_owner = models.User(email="other@example.com", display_name="other")
    db.add(dest_owner); db.commit(); db.refresh(dest_owner)
    dest = models.Organization(name="OtherOrg", created_by=dest_owner.id)
    db.add(dest); db.commit(); db.refresh(dest)
    # no membership for user in dest org -> forbidden (user not superadmin)
    r = client.post(
        f"/bulk-operations/organizations/{org.id}/bulk-move",
        json={"destination_organization_id": str(dest.id)},
        headers=_h(user),
    )
    assert r.status_code == 403
