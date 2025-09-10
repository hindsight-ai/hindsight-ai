import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app
from core.db import models
from sqlalchemy.orm import Session
import sqlalchemy


def _headers(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def test_add_member_invalid_role_rejected(db_session: Session, client):
    import os
    os.environ["ADMIN_EMAILS"] = "owneruser@example.com"
    owner_headers = _headers("owneruser")
    # Create organization
    r = client.post("/organizations/", json={"name": "RoleOrg", "slug": "roleorg"}, headers=owner_headers)
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]

    # Try invalid role
    r = client.post(f"/organizations/{org_id}/members", json={"email": "x@example.com", "role": "badrole"}, headers=owner_headers)
    assert r.status_code == 422


def test_member_role_change_audit_log(db_session: Session, client):
    import os
    os.environ["ADMIN_EMAILS"] = "changer@example.com"
    owner_headers = _headers("changer")
    r = client.post("/organizations/", json={"name": "RoleChangeOrg", "slug": "rolechg"}, headers=owner_headers)
    assert r.status_code == 201
    org_id = r.json()["id"]

    # Add member as viewer (default)
    r = client.post(f"/organizations/{org_id}/members", json={"email": "viewer@example.com"}, headers=owner_headers)
    assert r.status_code == 201

    # Get newly created member id
    session: Session = db_session
    member_user = session.query(models.User).filter(models.User.email == "viewer@example.com").first()
    assert member_user

    # Change role to editor
    r = client.put(f"/organizations/{org_id}/members/{member_user.id}", json={"role": "editor"}, headers=owner_headers)
    assert r.status_code == 200

    # Verify an audit log exists with role change
    from core.db import crud
    logs = crud.get_audit_logs(session, organization_id=uuid.UUID(org_id))
    role_change_logs = [l for l in logs if l.action_type == "member_role_change"]
    assert role_change_logs, "Expected member_role_change audit log"
    raw_meta = getattr(role_change_logs[0], 'metadata', None)
    if isinstance(raw_meta, dict):
        meta_dict = raw_meta
    else:
        meta_dict = getattr(role_change_logs[0], 'metadata_json', {}) or {}
    assert meta_dict.get("new_role") == "editor"