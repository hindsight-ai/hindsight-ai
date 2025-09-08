import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _h(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def test_agent_create_personal_and_duplicate_conflict(db_session):
    client = TestClient(main_app)
    headers = _h("alice")
    payload = {"agent_name": "Alpha", "visibility_scope": "personal"}
    r = client.post("/agents/", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    # Duplicate
    r2 = client.post("/agents/", json=payload, headers=headers)
    assert r2.status_code in (400, 409)


def test_agent_public_forbidden_for_non_superadmin(db_session):
    client = TestClient(main_app)
    headers = _h("bob")
    r = client.post("/agents/", json={"agent_name": "PublicX", "visibility_scope": "public"}, headers=headers)
    assert r.status_code == 403


def test_agent_list_filters_personal_scope(db_session):
    client = TestClient(main_app)
    headers = _h("carol")
    # Create 2 personal agents
    for name in ["A1", "A2"]:
        client.post("/agents/", json={"agent_name": name, "visibility_scope": "personal"}, headers=headers)
    r = client.get("/agents/", headers=headers)
    assert r.status_code == 200
    data = r.json()
    names = {a["agent_name"] for a in data}
    assert {"A1", "A2"}.issubset(names)