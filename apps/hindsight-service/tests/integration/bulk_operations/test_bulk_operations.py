"""Integration tests for bulk operations using real database fixtures.

Legacy mock-based tests were removed to exercise real permission logic.
"""

import uuid
import pytest
from core.db import models, crud, schemas


def _headers(email: str):
    user_part = email.split('@')[0]
    return {"x-auth-request-user": user_part, "x-auth-request-email": email}


"""Fixtures removed: rely on shared Postgres transactional session + client from root tests.conftest."""


@pytest.fixture
def org_owner(db):
    user = models.User(email="owner_it@example.com", display_name="owner")
    db.add(user); db.commit(); db.refresh(user)
    org = models.Organization(name="BulkOrg", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)
    membership = models.OrganizationMembership(organization_id=org.id, user_id=user.id, role='owner', can_read=True, can_write=True)
    db.add(membership); db.commit()
    return user, org


@pytest.fixture
def second_org(db, org_owner):
    user, _ = org_owner
    org2 = models.Organization(name="DestOrg", created_by=user.id)
    db.add(org2); db.commit(); db.refresh(org2)
    # Ensure user has owner membership in destination organization as well
    membership = models.OrganizationMembership(
        organization_id=org2.id,
        user_id=user.id,
        role='owner',
        can_read=True,
        can_write=True,
    )
    db.add(membership); db.commit()
    return org2


def test_get_organization_inventory_forbidden(client, db):
    other_owner = models.User(email="other@example.com", display_name="other")
    db.add(other_owner); db.commit(); db.refresh(other_owner)
    foreign_org = models.Organization(name="ForeignOrg", created_by=other_owner.id)
    db.add(foreign_org); db.commit(); db.refresh(foreign_org)
    headers = _headers("unauth@example.com")
    resp = client.get(f"/bulk-operations/organizations/{foreign_org.id}/inventory", headers=headers)
    assert resp.status_code == 403


def test_bulk_move_no_destination(client, org_owner):
    user, org = org_owner
    headers = _headers(user.email)
    resp = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json={}, headers=headers)
    assert resp.status_code == 422


def test_bulk_move_both_destinations(client, org_owner):
    user, org = org_owner
    headers = _headers(user.email)
    body = {"destination_organization_id": str(uuid.uuid4()), "destination_owner_user_id": str(uuid.uuid4())}
    resp = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json=body, headers=headers)
    assert resp.status_code == 422


def test_bulk_move_forbidden_destination(client, org_owner, db):
    user, org = org_owner
    foreign_owner = models.User(email="foreign@example.com", display_name="f")
    db.add(foreign_owner); db.commit(); db.refresh(foreign_owner)
    dest_org = models.Organization(name="ForeignDest", created_by=foreign_owner.id)
    db.add(dest_org); db.commit(); db.refresh(dest_org)
    headers = _headers(user.email)
    resp = client.post(f"/bulk-operations/organizations/{org.id}/bulk-move", json={"destination_organization_id": str(dest_org.id)}, headers=headers)
    assert resp.status_code == 403


def test_bulk_move_agent_conflict(client, org_owner, second_org, db):
    import os
    os.environ["ADMIN_EMAILS"] = "owner_it@example.com"
    user, source_org = org_owner
    dest_org = second_org
    crud.create_agent(db, schemas.AgentCreate(agent_name="dup", visibility_scope="organization", organization_id=source_org.id))
    crud.create_agent(db, schemas.AgentCreate(agent_name="dup", visibility_scope="organization", organization_id=dest_org.id))
    headers = _headers(user.email)
    resp = client.post(
        f"/bulk-operations/organizations/{source_org.id}/bulk-move",
        json={"destination_organization_id": str(dest_org.id), "resource_types": ["agents"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["conflicts"]["agents"]) == 1


def test_bulk_move_keyword_conflict(client, org_owner, second_org, db):
    import os
    os.environ["ADMIN_EMAILS"] = "owner_it@example.com"
    user, source_org = org_owner
    dest_org = second_org
    crud.create_keyword(db, schemas.KeywordCreate(keyword_text="kdup", visibility_scope="organization", organization_id=source_org.id))
    crud.create_keyword(db, schemas.KeywordCreate(keyword_text="kdup", visibility_scope="organization", organization_id=dest_org.id))
    headers = _headers(user.email)
    resp = client.post(
        f"/bulk-operations/organizations/{source_org.id}/bulk-move",
        json={"destination_organization_id": str(dest_org.id), "resource_types": ["keywords"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["conflicts"]["keywords"]) == 1


def test_bulk_move_no_dry_run(client, org_owner, second_org, monkeypatch):
    import os
    os.environ["ADMIN_EMAILS"] = "owner_it@example.com"
    from core import bulk_operations_worker as worker
    invoked = {"called": False}
    def fake_move(op_id, user_id, org_id, payload):
        invoked["called"] = True
    monkeypatch.setattr(worker, "perform_bulk_move", fake_move)
    user, source_org = org_owner
    dest_org = second_org
    headers = _headers(user.email)
    resp = client.post(
        f"/bulk-operations/organizations/{source_org.id}/bulk-move",
        json={"destination_organization_id": str(dest_org.id), "dry_run": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    assert invoked["called"] is True


def test_bulk_delete_no_dry_run(client, org_owner, monkeypatch):
    import os
    os.environ["ADMIN_EMAILS"] = "owner_it@example.com"
    from core import bulk_operations_worker as worker
    invoked = {"called": False}
    def fake_delete(op_id, user_id, org_id, payload):
        invoked["called"] = True
    monkeypatch.setattr(worker, "perform_bulk_delete", fake_delete)
    user, org = org_owner
    headers = _headers(user.email)
    resp = client.post(
        f"/bulk-operations/organizations/{org.id}/bulk-delete",
        json={"dry_run": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    assert invoked["called"] is True


def test_get_operation_status_forbidden(client, org_owner):
    user, org = org_owner
    headers = _headers(user.email)
    resp = client.get(f"/bulk-operations/admin/operations/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 403
