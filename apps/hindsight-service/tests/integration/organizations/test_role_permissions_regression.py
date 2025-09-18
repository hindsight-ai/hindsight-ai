import os
import uuid

from core.db import models


def _headers(user: str):
    # match project test helpers: x-auth-request headers
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def test_editor_has_write_on_add_and_accept(db_session, client):
    # Setup admin as owner
    os.environ["ADMIN_EMAILS"] = "owneruser@example.com"
    owner_headers = _headers("owneruser")

    # Create org
    r = client.post("/organizations/", json={"name": "RoleTestOrg", "slug": "roletestorg"}, headers=owner_headers)
    assert r.status_code == 201
    org_id = r.json()["id"]

    # Add editor via members endpoint
    r = client.post(f"/organizations/{org_id}/members", json={"email": "editor1@example.com", "role": "editor"}, headers=owner_headers)
    assert r.status_code == 201

    # List members and ensure editor has can_write True
    r = client.get(f"/organizations/{org_id}/members", headers=owner_headers)
    assert r.status_code == 200
    members = r.json()
    editor_member = next((m for m in members if m["email"] == "editor1@example.com"), None)
    assert editor_member is not None
    assert editor_member["role"] == "editor"
    assert editor_member["can_write"] is True

    # Invite another editor and accept via token
    r = client.post(f"/organizations/{org_id}/invitations", json={"email": "editor2@example.com", "role": "editor"}, headers=owner_headers)
    assert r.status_code == 201
    invite = r.json()

    # Accept using the accept endpoint with token in query string (token should override auth)
    accept_headers = {"x-auth-request-email": "editor2@example.com"}
    r = client.post(f"/organizations/{org_id}/invitations/{invite['id']}/accept?token={invite.get('token')}", headers=accept_headers)
    # accept may redirect or return 200/201 depending on implementation; ensure it's not a server error
    assert r.status_code in (200, 201)

    r = client.get(f"/organizations/{org_id}/members", headers=owner_headers)
    members = r.json()
    editor2 = next((m for m in members if m["email"] == "editor2@example.com"), None)
    assert editor2 is not None
    assert editor2["role"] == "editor"
    assert editor2["can_write"] is True


def test_updating_role_applies_defaults(db_session, client):
    os.environ["ADMIN_EMAILS"] = "owneruser@example.com"
    owner_headers = _headers("owneruser")

    # Create org and member
    r = client.post("/organizations/", json={"name": "RoleUpdateOrg", "slug": "roleupdateorg"}, headers=owner_headers)
    assert r.status_code == 201
    org_id = r.json()["id"]

    # Add a viewer manually (viewer has no write by default)
    r = client.post(f"/organizations/{org_id}/members", json={"email": "viewer@example.com", "role": "viewer"}, headers=owner_headers)
    assert r.status_code == 201

    # Find the member id
    r = client.get(f"/organizations/{org_id}/members", headers=owner_headers)
    members = r.json()
    member = next((m for m in members if m["email"] == "viewer@example.com"), None)
    assert member is not None

    # Update role to editor without explicit can_write
    member_user_id = member["user_id"]
    # Confirm initial member has no write
    r = client.get(f"/organizations/{org_id}/members", headers=owner_headers)
    members = r.json()
    before = next((m for m in members if m["email"] == "viewer@example.com"), None)
    assert before is not None
    assert before["can_write"] is False

    # Update role to editor without explicit can_write
    r = client.put(f"/organizations/{org_id}/members/{member_user_id}", json={"role": "editor"}, headers=owner_headers)
    assert r.status_code == 200

    r = client.get(f"/organizations/{org_id}/members", headers=owner_headers)
    members = r.json()
    updated = next((m for m in members if m["email"] == "viewer@example.com"), None)
    assert updated is not None
    assert updated["role"] == "editor"
    assert updated["can_write"] is True
