import uuid
from fastapi.testclient import TestClient
from core.api.main import app
from unittest.mock import patch
from core.db import models, crud

client = TestClient(app)


def auth():
    return {"x-auth-request-email": "kwtester@example.com", "x-auth-request-user": "Kw Tester"}


def _setup_user_and_org(db):
    user = models.User(email="kwtester@example.com", display_name="Kw Tester")
    db.add(user); db.flush()
    org = models.Organization(name="KwOrg", created_by=user.id)
    db.add(org); db.flush()
    mem = models.OrganizationMembership(organization_id=org.id, user_id=user.id, role="owner", can_read=True, can_write=True)
    db.add(mem); db.commit(); db.refresh(org)
    return user, org


def test_keyword_create_update_delete_audits(db_session):
    # Arrange
    user, org = _setup_user_and_org(db_session)
    user_id = user.id
    org_id = org.id

    # Create keyword (organization scope)
    create_payload = {"keyword_text": "alpha", "visibility_scope": "organization", "organization_id": str(org_id)}
    # Patch membership lookup to show user as owner (write perms)
    # Patch in the module where it's imported by the active endpoints (main)
    with patch("core.api.main.get_user_memberships") as mock_memberships:
        mock_memberships.return_value = [{"organization_id": str(org_id), "role": "owner", "can_write": True}]
        r = client.post("/keywords/", json=create_payload, headers=auth())
    assert r.status_code == 201, r.text
    kw_id = r.json()["keyword_id"]

    # Update keyword text
    update_payload = {"keyword_text": "alpha2"}
    with patch("core.api.main.get_user_memberships") as mock_memberships:
        mock_memberships.return_value = [{"organization_id": str(org_id), "role": "owner", "can_write": True}]
        r2 = client.put(f"/keywords/{kw_id}", json=update_payload, headers=auth())
    assert r2.status_code == 200, r2.text

    # Delete keyword
    with patch("core.api.main.get_user_memberships") as mock_memberships:
        mock_memberships.return_value = [{"organization_id": str(org_id), "role": "owner", "can_write": True}]
        r3 = client.delete(f"/keywords/{kw_id}", headers=auth())
    assert r3.status_code == 204, r3.text

    # Verify audit logs
    logs = crud.get_audit_logs(db_session, organization_id=org_id)
    actions = [(l.action_type, str(l.target_id)) for l in logs]
    assert any(a == "keyword_create" and tid == kw_id for a, tid in actions), actions
    assert any(a == "keyword_update" and tid == kw_id for a, tid in actions), actions
    assert any(a == "keyword_delete" and tid == kw_id for a, tid in actions), actions
