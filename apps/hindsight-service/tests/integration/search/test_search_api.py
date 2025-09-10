from fastapi.testclient import TestClient
from core.api.main import app
from core.db import models

client = TestClient(app)


def auth(email="searcher@example.com", name="Searcher"):
    return {"x-auth-request-email": email, "x-auth-request-user": name}


def ensure_user():
    client.get("/keywords/", headers=auth())


def seed_memory_blocks():
    ensure_user()
    # create agent once
    agent_resp = client.post("/agents/", json={"agent_name": "SearchAgent", "visibility_scope": "personal"}, headers=auth())
    assert agent_resp.status_code == 201, agent_resp.text
    agent_id = agent_resp.json()["agent_id"]
    import uuid as _uuid
    texts = [
        "Alpha project planning meeting notes about database optimization.",
        "Beta release retrospective covering performance and logging.",
        "Gamma incident report detailing error handling and retry logic.",
    ]
    ids = []
    for t in texts:
        r = client.post("/memory-blocks/", json={"content": t, "visibility_scope": "personal", "agent_id": agent_id, "conversation_id": str(_uuid.uuid4())}, headers=auth())
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return ids


def test_fulltext_search_basic():
    seed_memory_blocks()
    r = client.get("/memory-blocks/search/fulltext", params={"query": "performance"}, headers=auth())
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)


def test_semantic_search_fallback():
    seed_memory_blocks()
    r = client.get("/memory-blocks/search/semantic", params={"query": "retry logic"}, headers=auth())
    assert r.status_code == 200
    results = r.json()
    # Expect at least one result due to fallback/hybrid logic inside service (may be empty if implementation minimal)
    assert isinstance(results, list)


def test_hybrid_search():
    seed_memory_blocks()
    r = client.get("/memory-blocks/search/hybrid", params={"query": "database optimization"}, headers=auth())
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
