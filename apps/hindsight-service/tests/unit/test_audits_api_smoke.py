import uuid
from fastapi.testclient import TestClient

from core.api.main import app


client = TestClient(app)


def _h(user, email):
    return {"x-auth-request-user": user, "x-auth-request-email": email}


def test_audits_list_with_org_filter():
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    # Create org to generate an audit log
    r_org = client.post("/organizations/", json={"name": f"AuditOrg_{uuid.uuid4().hex[:6]}"}, headers=_h("admin", admin_email))
    assert r_org.status_code == 201
    org_id = r_org.json()["id"]

    # List audits for org as org owner
    r_aud = client.get(f"/audits/?organization_id={org_id}", headers=_h("admin", admin_email))
    assert r_aud.status_code == 200
    logs = r_aud.json()
    assert isinstance(logs, list)
    # The organization_create action should be present
    assert any(l.get("action_type") == "organization_create" for l in logs)

