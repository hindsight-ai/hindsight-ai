import os
import uuid
import pytest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from core.db import models
from core.db.database import get_db
from core.api.main import app
from core.api import bulk_operations
from fastapi.testclient import TestClient
from fastapi import HTTPException


def auth(email="admin@example.com", name="Admin"):
    return {"x-auth-request-email": email, "x-auth-request-user": name}


def create_org(db, name="BulkOrg"):
    org = models.Organization(name=name)
    db.add(org); db.commit(); db.refresh(org)
    return org


def create_membership(db, user_id, org_id, role="owner", *, can_write=True, can_read=True):
    # Pass UUID objects directly; SQLAlchemy's PostgreSQL UUID type with SQLite shim
    # expects UUID instances, not stringified values.
    m = models.OrganizationMembership(
        user_id=user_id,
        organization_id=org_id,
        role=role,
        can_write=can_write,
        can_read=can_read,
    )
    db.add(m)
    db.commit()
    return m


def get_user(db, email):
    return db.query(models.User).filter(models.User.email == email).first()


@pytest.fixture
def client():
    return TestClient(app, headers={"X-Active-Scope": "personal"})


def test_bulk_move_dry_run_and_start(client):
    import os
    os.environ["ADMIN_EMAILS"] = "admin@example.com"
    # Trigger user creation via auth path
    client.get("/keywords/", headers=auth())
    # Use dependency override session
    from tests.conftest import _current_session
    db = _current_session.get()
    user = get_user(db, "admin@example.com")
    org = create_org(db)
    create_membership(db, user.id, org.id, role="owner")
    agent = models.Agent(agent_name="Mover", visibility_scope="organization", organization_id=org.id)
    db.add(agent); db.commit(); db.refresh(agent)
    payload = {"dry_run": True, "destination_owner_user_id": str(user.id), "resource_types": ["agents"]}
    r = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json=payload, headers=auth())
    assert r.status_code == 200, r.text
    assert r.json()["resources_to_move"]["agents"] >= 1
    payload["dry_run"] = False
    r2 = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json=payload, headers=auth())
    assert r2.status_code == 200, r2.text
    assert "operation_id" in r2.json()


def test_bulk_delete_dry_run(client):
    client.get("/keywords/", headers=auth())
    from tests.conftest import _current_session
    db = _current_session.get()
    user = get_user(db, "admin@example.com")
    org = create_org(db, name="DelOrg")
    create_membership(db, user.id, org.id, role="owner")
    agent = models.Agent(agent_name="DelAgent", visibility_scope="organization", organization_id=org.id)
    db.add(agent); db.commit(); db.refresh(agent)
    mb = models.MemoryBlock(
        content="to delete",
        visibility_scope="organization",
        organization_id=org.id,
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
    )
    db.add(mb); db.commit(); db.refresh(mb)
    payload = {"dry_run": True, "resource_types": ["memory_blocks"]}
    r = client.post(f"/bulk-operations/organizations/{org.id}/bulk-delete", json=payload, headers=auth())
    assert r.status_code == 200
    assert r.json()["resources_to_delete"]["memory_blocks"] >= 1


def test_get_operation_status_forbidden_and_not_found(client):
    # call with non-superadmin (regular user)
    client.get("/keywords/", headers=auth())
    fake_id = str(uuid.uuid4())
    r = client.get(f"/bulk-operations/admin/operations/{fake_id}", headers=auth())
    # Should be forbidden because user not superadmin
    assert r.status_code == 403


def test_bulk_delete_preview_allows_member_without_write(client):
    os.environ.pop("ADMIN_EMAILS", None)
    client.get("/keywords/", headers=auth())
    from tests.conftest import _current_session
    db = _current_session.get()
    user = get_user(db, "admin@example.com")
    org = create_org(db, name="PreviewOrg")
    create_membership(db, user.id, org.id, role="viewer", can_write=False, can_read=True)

    resp = client.post(
        f"/bulk-operations/organizations/{org.id}/bulk-delete",
        json={"dry_run": True, "resource_types": ["agents", "keywords", "memory_blocks"]},
        headers=auth(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["resources_to_delete"].keys()) == {"agents", "keywords", "memory_blocks"}


def test_bulk_delete_requires_manage_permission_for_execution(client):
    os.environ.pop("ADMIN_EMAILS", None)
    client.get("/keywords/", headers=auth())
    from tests.conftest import _current_session
    db = _current_session.get()
    user = get_user(db, "admin@example.com")
    org = create_org(db, name="NoWriteOrg")

    resp = client.post(
        f"/bulk-operations/organizations/{org.id}/bulk-delete",
        json={"dry_run": False, "resource_types": ["agents"]},
        headers=auth(),
    )
    assert resp.status_code == 403


def test_bulk_delete_start_triggers_async_task(client, monkeypatch):
    os.environ["ADMIN_EMAILS"] = "admin@example.com"
    client.get("/keywords/", headers=auth())
    from tests.conftest import _current_session
    db = _current_session.get()
    user = get_user(db, "admin@example.com")
    org = create_org(db, name="ExecOrg")
    create_membership(db, user.id, org.id, role="owner", can_write=True)

    from core import async_bulk_operations
    async_stub = AsyncMock(return_value=None)
    monkeypatch.setattr(async_bulk_operations, "execute_bulk_operation_async", async_stub)

    resp = client.post(
        f"/bulk-operations/organizations/{org.id}/bulk-delete",
        json={"dry_run": False, "resource_types": ["keywords"]},
        headers=auth(),
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "started"
    assert "operation_id" in payload
    assert async_stub.await_count == 1


def test_get_operation_status_not_found_for_superadmin(db):
    dummy_user = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        bulk_operations.get_operation_status(
            uuid.uuid4(),
            db=db,
            user_context=(dummy_user, {"is_superadmin": True, "memberships": [], "memberships_by_org": {}}),
        )
    assert exc.value.status_code == 404
