import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _headers(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def test_keyword_get_single():
    client = TestClient(main_app)
    h = _headers("user")
    # Create agent first
    r = client.post("/agents/", json={"agent_name": "KeywordAgent", "description": "for keywords"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Create memory block with keywords
    r2 = client.post("/memory-blocks/", json={
        "content": "content with keywords",
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "keywords": ["test", "keyword"]
    }, headers=h)
    assert r2.status_code == 201
    # Get keywords
    r3 = client.get("/keywords/", headers=h)
    assert r3.status_code == 200
    keywords = r3.json()
    assert isinstance(keywords, list)


def test_keyword_update():
    client = TestClient(main_app)
    h = _headers("user")
    # Create agent first
    r = client.post("/agents/", json={"agent_name": "UpdateKeywordAgent", "description": "for keyword update"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Create memory block with keywords
    r2 = client.post("/memory-blocks/", json={
        "content": "content for keyword update",
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "keywords": ["old", "keyword"]
    }, headers=h)
    assert r2.status_code == 201
    block_id = r2.json()["id"]
    # Update keywords
    r3 = client.put(f"/memory-blocks/{block_id}", json={
        "content": "updated content",
        "keywords": ["new", "keyword"]
    }, headers=h)
    assert r3.status_code == 200


def test_keyword_delete():
    client = TestClient(main_app)
    h = _headers("user")
    # Create agent first
    r = client.post("/agents/", json={"agent_name": "DeleteKeywordAgent", "description": "for keyword delete"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Create memory block with keywords
    r2 = client.post("/memory-blocks/", json={
        "content": "content for keyword delete",
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "keywords": ["delete", "test"]
    }, headers=h)
    assert r2.status_code == 201
    block_id = r2.json()["id"]
    # Delete memory block (which should delete keywords)
    r3 = client.delete(f"/memory-blocks/{block_id}", headers=h)
    assert r3.status_code == 204
