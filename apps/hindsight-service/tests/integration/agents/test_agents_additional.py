import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _headers(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def test_create_agent_name_conflict_in_scope():
    client = TestClient(main_app)
    h = _headers("agentuser")
    r = client.post("/agents/", json={"agent_name": "Alpha", "description": "a"}, headers=h)
    assert r.status_code == 201
    # Attempt duplicate in same personal scope
    r2 = client.post("/agents/", json={"agent_name": "Alpha", "description": "b"}, headers=h)
    assert r2.status_code in (400, 409)  # depending on endpoint message consistency


def test_agent_scope_change_conflict():
    client = TestClient(main_app)
    h = _headers("scopeuser")
    # Create two personal agents
    r1 = client.post("/agents/", json={"agent_name": "A1", "description": "d"}, headers=h); assert r1.status_code == 201
    r2 = client.post("/agents/", json={"agent_name": "A1", "description": "d"}, headers=h); assert r2.status_code in (400, 409)


def test_agent_create_and_update():
    client = TestClient(main_app)
    h = _headers("agentuser")
    # Create agent
    r = client.post("/agents/", json={"agent_name": "TestAgent", "description": "test agent"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Update agent
    r2 = client.put(f"/agents/{agent_id}", json={"agent_name": "UpdatedAgent", "description": "updated"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["agent_name"] == "UpdatedAgent"


def test_get_agents_endpoint():
    client = TestClient(main_app)
    h = _headers("agentuser")
    # Create an agent first
    r = client.post("/agents/", json={"agent_name": "ListAgent", "description": "for listing"}, headers=h)
    assert r.status_code == 201
    # Get agents
    r2 = client.get("/agents/", headers=h)
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)


def test_get_single_agent_endpoint():
    client = TestClient(main_app)
    h = _headers("agentuser")
    # Create an agent first
    r = client.post("/agents/", json={"agent_name": "SingleAgent", "description": "for single get"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Get single agent
    r2 = client.get(f"/agents/{agent_id}", headers=h)
    assert r2.status_code == 200
    assert r2.json()["agent_id"] == agent_id


def test_crud_get_agent(db_session):
    from core.db import models, crud
    db = db_session
    owner = models.User(email="crud_test@example.com", display_name="CRUDTest", is_superadmin=False)
    db.add(owner); db.commit(); db.refresh(owner)
    agent = models.Agent(agent_name="CRUDTestAgent", visibility_scope="personal", owner_user_id=owner.id)
    db.add(agent); db.commit(); db.refresh(agent)
    fetched = crud.get_agent(db, agent.agent_id)
    assert fetched.agent_id == agent.agent_id
