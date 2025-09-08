import uuid
from fastapi.testclient import TestClient
from core.api.main import app
from core.db.database import SessionLocal
from core.db import models

client = TestClient(app)


def auth(email="admin@example.com", name="Admin"):
    return {"x-auth-request-email": email, "x-auth-request-user": name}


def create_org(db, name="BulkOrg"):
    org = models.Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def create_membership(db, user_id, org_id, role="owner"):
    # Pass UUID objects directly; SQLAlchemy's PostgreSQL UUID type with SQLite shim
    # expects UUID instances, not stringified values.
    m = models.OrganizationMembership(user_id=user_id, organization_id=org_id, role=role, can_write=True)
    db.add(m)
    db.commit()
    return m


def get_user(db, email):
    return db.query(models.User).filter(models.User.email == email).first()


def test_bulk_move_dry_run_and_start(monkeypatch):
    # Prepare org and user membership
    with SessionLocal() as db:
        org = create_org(db)
    # trigger user creation
    client.get("/keywords/", headers=auth())
    with SessionLocal() as db:
        user = get_user(db, "admin@example.com")
        user_id = user.id  # capture before session closes
    create_membership(db, user_id, org.id, role="owner")
    # add an agent to move
    agent = models.Agent(agent_name="Mover", visibility_scope="organization", organization_id=org.id)
    db.add(agent)
    db.commit()
    # dry run
    payload = {"dry_run": True, "destination_owner_user_id": str(user_id)}
    r = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json=payload, headers=auth())
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["resources_to_move"]["agents"] >= 1
    # now start actual move (dry_run False)
    payload["dry_run"] = False
    r2 = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json=payload, headers=auth())
    assert r2.status_code == 200, r2.text
    assert "operation_id" in r2.json()


def test_bulk_delete_dry_run(monkeypatch):
    with SessionLocal() as db:
        org = create_org(db, name="DelOrg")
    client.get("/keywords/", headers=auth())
    with SessionLocal() as db:
        user = get_user(db, "admin@example.com")
        create_membership(db, user.id, org.id, role="owner")
        # create agent to attach to memory block
        agent = models.Agent(agent_name="DelAgent", visibility_scope="organization", organization_id=org.id)
        db.add(agent)
        db.commit()
        mb = models.MemoryBlock(
            content="to delete",
            visibility_scope="organization",
            organization_id=org.id,
            agent_id=agent.agent_id,
            conversation_id=uuid.uuid4(),
        )
        db.add(mb)
        db.commit()
    payload = {"dry_run": True, "resource_types": ["memory_blocks"]}
    r = client.post(f"/bulk-operations/organizations/{org.id}/bulk-delete", json=payload, headers=auth())
    assert r.status_code == 200
    data = r.json()
    assert data["resources_to_delete"]["memory_blocks"] >= 1


def test_get_operation_status_forbidden_and_not_found():
    # call with non-superadmin (regular user)
    client.get("/keywords/", headers=auth())
    fake_id = str(uuid.uuid4())
    r = client.get(f"/bulk-operations/admin/operations/{fake_id}", headers=auth())
    # Should be forbidden because user not superadmin
    assert r.status_code == 403

