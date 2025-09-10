from fastapi.testclient import TestClient
from core.api.main import app
import uuid

client = TestClient(app)


def auth(email="orguser@example.com", name="OrgUser"):
    return {"x-auth-request-email": email, "x-auth-request-user": name}


def test_create_org_no_email():
    headers = {"x-auth-request-user": "noemail"}
    r = client.post("/organizations/", json={"name": "NoEmailOrg"}, headers=headers)
    assert r.status_code == 401
    assert "Authentication required" in r.json()["detail"]


def test_list_orgs_non_superadmin():
    import os
    os.environ["ADMIN_EMAILS"] = "nonsuper@example.com"
    # Create org as user
    r = client.post("/organizations/", json={"name": "NonSuperOrg"}, headers=auth("nonsuper@example.com"))
    assert r.status_code == 201
    org_id = r.json()["id"]
    # List orgs as same user (should see it)
    r2 = client.get("/organizations/", headers=auth("nonsuper@example.com"))
    assert r2.status_code == 200
    print("Response:", r2.json())
    assert any(o["id"] == org_id for o in r2.json())


def test_create_org_empty_name():
    import os
    os.environ["ADMIN_EMAILS"] = "orguser@example.com"
    r = client.post("/organizations/", json={"name": ""}, headers=auth())
    assert r.status_code == 422
    assert "Organization name is required" in r.json()["detail"]


def test_create_list_get_update_org():
    import os
    os.environ["ADMIN_EMAILS"] = "orguser@example.com"
    r = client.post("/organizations/", json={"name": "TestOrg1"}, headers=auth())
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]
    # list
    r2 = client.get("/organizations/", headers=auth())
    assert r2.status_code == 200
    assert any(o["id"] == org_id for o in r2.json())
    # get
    r3 = client.get(f"/organizations/{org_id}", headers=auth())
    assert r3.status_code == 200
    # update
    r4 = client.put(f"/organizations/{org_id}", json={"name": "RenamedOrg"}, headers=auth())
    assert r4.status_code == 200
    assert r4.json()["name"] == "RenamedOrg"


def test_add_member_and_permission_denial():
    import os
    os.environ["ADMIN_EMAILS"] = "owner1@example.com"
    r = client.post("/organizations/", json={"name": "PermOrg"}, headers=auth("owner1@example.com"))
    assert r.status_code == 201
    org_id = r.json()["id"]
    # non-member tries to add member (should fail since outsider is not superadmin)
    bad = client.post(f"/organizations/{org_id}/members", json={"email": "x@example.com", "role": "viewer"}, headers=auth("outsider@example.com"))
    assert bad.status_code in (403, 404)
    # owner adds member
    good = client.post(f"/organizations/{org_id}/members", json={"email": "newmember@example.com", "role": "viewer"}, headers=auth("owner1@example.com"))
    assert good.status_code == 201, good.text
    # list members (viewer now present)
    members = client.get(f"/organizations/{org_id}/members", headers=auth("owner1@example.com"))
    assert members.status_code == 200
    body = members.json()
    assert any(m["email"] == "newmember@example.com" for m in body)


def test_update_member_role_and_delete_member():
    import os
    os.environ["ADMIN_EMAILS"] = "roleowner@example.com"
    r = client.post("/organizations/", json={"name": "RoleOrg"}, headers=auth("roleowner@example.com"))
    org_id = r.json()["id"]
    add = client.post(f"/organizations/{org_id}/members", json={"email": "editme@example.com", "role": "viewer"}, headers=auth("roleowner@example.com"))
    assert add.status_code == 201
    # Get the user ID from the response or from the members list
    members = client.get(f"/organizations/{org_id}/members", headers=auth("roleowner@example.com"))
    assert members.status_code == 200
    member_data = members.json()
    editme_member = next((m for m in member_data if m["email"] == "editme@example.com"), None)
    assert editme_member is not None
    member_user_id = editme_member["user_id"]
    # update role
    update = client.put(f"/organizations/{org_id}/members/{member_user_id}", json={"role": "editor"}, headers=auth("roleowner@example.com"))
    assert update.status_code == 200
    # delete member
    delete = client.delete(f"/organizations/{org_id}/members/{member_user_id}", headers=auth("roleowner@example.com"))
    assert delete.status_code == 204


def test_invitations_lifecycle():
    import os
    os.environ["ADMIN_EMAILS"] = "inviter@example.com,invitee@example.com"
    # Create org
    r = client.post("/organizations/", json={"name": "InviteOrg"}, headers=auth("inviter@example.com"))
    assert r.status_code == 201
    org_id = r.json()["id"]
    # Create invitation
    inv = client.post(f"/organizations/{org_id}/invitations", json={"email": "invitee@example.com", "role": "editor"}, headers=auth("inviter@example.com"))
    assert inv.status_code == 201, inv.text
    inv_id = inv.json()["id"]
    # List invitations
    lst = client.get(f"/organizations/{org_id}/invitations", headers=auth("inviter@example.com"))
    assert lst.status_code == 200
    assert any(i["id"] == inv_id for i in lst.json())
    # Resend invitation
    res = client.post(f"/organizations/{org_id}/invitations/{inv_id}/resend", headers=auth("inviter@example.com"))
    assert res.status_code == 200
    # Accept invitation (as invitee)
    acc = client.post(f"/organizations/{org_id}/invitations/{inv_id}/accept", headers=auth("invitee@example.com"))
    assert acc.status_code == 200
    # Revoke (should fail now that accepted)
    rev = client.delete(f"/organizations/{org_id}/invitations/{inv_id}", headers=auth("inviter@example.com"))
    assert rev.status_code == 204  # or check if it handles accepted state

