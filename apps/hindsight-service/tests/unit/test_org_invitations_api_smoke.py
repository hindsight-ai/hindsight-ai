import uuid
from fastapi.testclient import TestClient

from core.api.main import app


client = TestClient(app)


def _h(user, email):
    return {"x-auth-request-user": user, "x-auth-request-email": email}


def test_org_invitations_lifecycle_smoke():
    owner_email = f"owner_{uuid.uuid4().hex[:8]}@example.com"
    # Create organization as owner
    r_org = client.post("/organizations/", json={"name": f"Org_{uuid.uuid4().hex[:6]}"}, headers=_h("owner", owner_email))
    assert r_org.status_code == 201, r_org.text
    org_id = r_org.json()["id"]

    # Create invitation
    invitee_email = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
    r_inv = client.post(
        f"/organizations/{org_id}/invitations",
        json={"email": invitee_email, "role": "viewer"},
        headers=_h("owner", owner_email),
    )
    assert r_inv.status_code == 201, r_inv.text
    inv_id = r_inv.json()["id"]

    # List invitations
    r_list = client.get(f"/organizations/{org_id}/invitations", headers=_h("owner", owner_email))
    assert r_list.status_code == 200
    assert any(i["id"] == inv_id for i in r_list.json())

    # Resend invitation
    r_resend = client.post(f"/organizations/{org_id}/invitations/{inv_id}/resend", headers=_h("owner", owner_email))
    assert r_resend.status_code == 200

    # Create a second invitation to exercise accept path
    invitee2_email = f"invitee2_{uuid.uuid4().hex[:8]}@example.com"
    r_inv2 = client.post(
        f"/organizations/{org_id}/invitations",
        json={"email": invitee2_email, "role": "viewer"},
        headers=_h("owner", owner_email),
    )
    assert r_inv2.status_code == 201
    inv2_id = r_inv2.json()["id"]

    # Accept second invitation as invitee
    r_accept = client.post(
        f"/organizations/{org_id}/invitations/{inv2_id}/accept",
        headers=_h("invitee2", invitee2_email),
    )
    assert r_accept.status_code == 200

    # Revoke first invitation
    r_revoke = client.delete(f"/organizations/{org_id}/invitations/{inv_id}", headers=_h("owner", owner_email))
    assert r_revoke.status_code == 204

