import os
import uuid
import pytest
from fastapi.testclient import TestClient

from core.api.main import app


def _h(email):
    return {"x-auth-request-user": email.split("@")[0], "x-auth-request-email": email}


@pytest.mark.usefixtures("db_session")
def test_orgs_create_list_manageable_and_admin(db_session, monkeypatch):
    client = TestClient(app)

    # Create an organization as a regular user
    owner_email = f"owner_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/organizations/", json={"name": "UnitOrg1"}, headers=_h(owner_email))
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]

    # List organizations for the owner (should include created org)
    r_list = client.get("/organizations/", headers=_h(owner_email))
    assert r_list.status_code == 200
    assert any(o["id"] == org_id for o in r_list.json())

    # Manageable orgs for owner (role owner) should include the org
    r_m = client.get("/organizations/manageable", headers=_h(owner_email))
    assert r_m.status_code == 200
    assert any(o["id"] == org_id for o in r_m.json())

    # Admin listing forbidden for non-superadmin
    r_admin_forbidden = client.get("/organizations/admin", headers=_h(owner_email))
    assert r_admin_forbidden.status_code == 403

    # Superadmin should list all organizations
    super_email = "superadmin@example.com"
    monkeypatch.setenv("ADMIN_EMAILS", super_email)
    # trigger superadmin user creation
    client.get("/keywords/", headers=_h(super_email))
    r_admin = client.get("/organizations/admin", headers=_h(super_email))
    assert r_admin.status_code == 200
    # Should see at least the previously created organization
    assert any(o["id"] == org_id for o in r_admin.json())

