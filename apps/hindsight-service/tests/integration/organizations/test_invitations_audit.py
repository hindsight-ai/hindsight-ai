import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app
from core.db import crud, models
from sqlalchemy.orm import Session


def _headers(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def _get_logs(session: Session, org_id):
    return crud.get_audit_logs(session, organization_id=uuid.UUID(str(org_id)))


def test_invitation_lifecycle_audit_logs(db_session: Session, client):
    import os
    os.environ["ADMIN_EMAILS"] = "invowner@example.com"
    owner_headers = _headers("invowner")

    # Create org
    r = client.post("/organizations/", json={"name": "InviteAuditOrg", "slug": "inviteaudit"}, headers=owner_headers)
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]

    # Create invitation
    invite_email = "invitee@example.com"
    r = client.post(f"/organizations/{org_id}/invitations", json={"email": invite_email, "role": "viewer"}, headers=owner_headers)
    assert r.status_code == 201, r.text
    invitation_id = r.json()["id"]

    logs = _get_logs(db_session, org_id)
    create_logs = [l for l in logs if l.action_type == "invitation_create"]
    assert create_logs, "Expected invitation_create audit log"

    # Resend invitation
    r = client.post(f"/organizations/{org_id}/invitations/{invitation_id}/resend", headers=owner_headers)
    assert r.status_code == 200
    logs = _get_logs(db_session, org_id)
    resend_logs = [l for l in logs if l.action_type == "invitation_resend"]
    assert resend_logs, "Expected invitation_resend audit log"

    # Accept invitation: need to simulate different user
    accept_headers = _headers("invitee")
    r = client.post(f"/organizations/{org_id}/invitations/{invitation_id}/accept", headers=accept_headers)
    assert r.status_code == 200, r.text
    logs = _get_logs(db_session, org_id)
    accept_logs = [l for l in logs if l.action_type == "invitation_accept"]
    assert accept_logs, "Expected invitation_accept audit log"


def test_invitation_revoke_audit_log(db_session: Session):
    import os
    os.environ["ADMIN_EMAILS"] = "revoker@example.com"
    client = TestClient(main_app)
    owner_headers = _headers("revoker")
    # Create org
    r = client.post("/organizations/", json={"name": "RevokeOrg", "slug": "revokeorg"}, headers=owner_headers)
    assert r.status_code == 201
    org_id = r.json()["id"]

    # Create invitation
    r = client.post(f"/organizations/{org_id}/invitations", json={"email": "torevoke@example.com", "role": "viewer"}, headers=owner_headers)
    assert r.status_code == 201
    invitation_id = r.json()["id"]

    # Revoke
    r = client.delete(f"/organizations/{org_id}/invitations/{invitation_id}", headers=owner_headers)
    assert r.status_code == 204

    logs = _get_logs(db_session, org_id)
    revoke_logs = [l for l in logs if l.action_type == "invitation_revoke"]
    assert revoke_logs, "Expected invitation_revoke audit log"
