import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _h(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com", "x-active-scope": "personal"}


def test_agent_create_no_email_forbidden():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    headers = {"x-auth-request-user": "noemail"}
    payload = {"agent_name": "NoEmailAgent", "visibility_scope": "personal"}
    r = client.post("/agents/", json=payload, headers=headers)
    assert r.status_code == 401
    assert "Authentication required" in r.json()["detail"]


def test_agent_public_forbidden_for_non_superadmin(db_session):
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    # Explicitly request public scope so endpoint enforces superadmin-only creation
    headers = {"x-auth-request-user": "bob", "x-auth-request-email": "bob@example.com", "X-Active-Scope": "public"}
    r = client.post("/agents/", json={"agent_name": "PublicX", "visibility_scope": "public"}, headers=headers)
    assert r.status_code == 403


def test_agent_get_other_personal_not_found(db_session):
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    # Create agent as alice
    headers_alice = _h("alice")
    payload = {"agent_name": "SecretAgent", "visibility_scope": "personal"}
    r = client.post("/agents/", json=payload, headers=headers_alice)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Try to get as bob
    headers_bob = _h("bob")
    r2 = client.get(f"/agents/{agent_id}", headers=headers_bob)
    assert r2.status_code == 404


def test_agent_delete_not_found():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    headers = _h("user")
    fake_agent_id = str(uuid.uuid4())
    r = client.delete(f"/agents/{fake_agent_id}", headers=headers)
    assert r.status_code == 404


def test_agent_delete_other_personal_forbidden(db_session):
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    # Create agent as alice
    headers_alice = _h("alice")
    payload = {"agent_name": "SecretAgent", "visibility_scope": "personal"}
    r = client.post("/agents/", json=payload, headers=headers_alice)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Try to delete as bob
    headers_bob = _h("bob")
    r2 = client.delete(f"/agents/{agent_id}", headers=headers_bob)
    assert r2.status_code == 403


def test_agent_update_not_found():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    headers = _h("user")
    fake_agent_id = str(uuid.uuid4())
    r = client.put(f"/agents/{fake_agent_id}", json={"agent_name": "NewName"}, headers=headers)
    assert r.status_code == 404


def test_agent_update_other_personal_forbidden(db_session):
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    # Create agent as alice
    headers_alice = _h("alice")
    payload = {"agent_name": "SecretAgent", "visibility_scope": "personal"}
    r = client.post("/agents/", json=payload, headers=headers_alice)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Try to update as bob
    headers_bob = _h("bob")
    r2 = client.put(f"/agents/{agent_id}", json={"agent_name": "NewName"}, headers=headers_bob)
    assert r2.status_code == 403


def test_agent_update_name_conflict(db_session):
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    headers = _h("alice")
    # Create first agent
    r1 = client.post("/agents/", json={"agent_name": "Agent1", "visibility_scope": "personal"}, headers=headers)
    assert r1.status_code == 201
    agent_id1 = r1.json()["agent_id"]
    # Create second agent
    r2 = client.post("/agents/", json={"agent_name": "Agent2", "visibility_scope": "personal"}, headers=headers)
    assert r2.status_code == 201
    agent_id2 = r2.json()["agent_id"]
    # Try to update first agent to same name as second
    r3 = client.put(f"/agents/{agent_id1}", json={"agent_name": "Agent2"}, headers=headers)
    assert r3.status_code == 409