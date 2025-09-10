import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _headers(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def test_guest_mode_readonly():
    client = TestClient(main_app)
    # POST without auth headers should return 401
    r = client.post("/agents/", json={"agent_name": "GuestAgent", "description": "test"})
    assert r.status_code == 401
    assert "Guest mode is read-only" in r.json()["detail"]
    # PUT without auth headers should return 401
    r2 = client.put("/agents/123", json={"agent_name": "UpdatedAgent"})
    assert r2.status_code == 401
    assert "Guest mode is read-only" in r2.json()["detail"]
    # DELETE without auth headers should return 401
    r3 = client.delete("/agents/123")
    assert r3.status_code == 401
    assert "Guest mode is read-only" in r3.json()["detail"]
    # PATCH without auth headers should return 401
    r4 = client.patch("/agents/123", json={"agent_name": "PatchedAgent"})
    assert r4.status_code == 401
    assert "Guest mode is read-only" in r4.json()["detail"]
    # GET should work fine (read-only is only for write operations)
    r5 = client.get("/agents/")
    assert r5.status_code == 200  # Should not be blocked
    # Test authenticated request to ensure call_next is executed
    h = _headers("authuser")
    r6 = client.post("/agents/", json={"agent_name": "AuthAgent", "description": "test"}, headers=h)
    assert r6.status_code == 201  # Should succeed with auth


def test_auth_no_email():
    client = TestClient(main_app)
    # Headers with user but no email
    headers = {"x-auth-request-user": "testuser"}
    r = client.post("/agents/", json={"agent_name": "NoEmailAgent", "description": "test"}, headers=headers)
    assert r.status_code == 401
    assert "Authentication required" in r.json()["detail"]


def test_create_agent_org_no_permission():
    import os
    os.environ["ADMIN_EMAILS"] = "admin@example.com"
    client = TestClient(main_app)
    h = _headers("user")
    # Create org
    r = client.post("/organizations/", json={"name": "NoPermOrg", "slug": "nopermorg"}, headers=h)
    assert r.status_code == 201
    org_id = r.json()["id"]
    # Try to create agent in org without membership
    r2 = client.post("/agents/", json={"agent_name": "NoPermAgent", "visibility_scope": "organization", "organization_id": org_id, "description": "test"}, headers=h)
    assert r2.status_code == 403
    assert "No write permission in target organization" in r2.json()["detail"]


def test_get_agent_not_found():
    client = TestClient(main_app)
    h = _headers("user")
    fake_agent_id = str(uuid.uuid4())
    r = client.get(f"/agents/{fake_agent_id}", headers=h)
    assert r.status_code == 404
    assert "Agent not found" in r.json()["detail"]
