import pytest
from fastapi.testclient import TestClient
from core.api.main import app
from core.db import models
from core.services.embedding_service import reset_embedding_service_for_tests

client = TestClient(app, headers={"X-Active-Scope": "personal"})


@pytest.fixture(autouse=True)
def enable_mock_embeddings(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "8")
    reset_embedding_service_for_tests()
    yield
    reset_embedding_service_for_tests()


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
    if results:
        assert "score_components" in results[0]


def test_semantic_search_returns_scored_results():
    seed_memory_blocks()
    r = client.get("/memory-blocks/search/semantic", params={"query": "retry logic"}, headers=auth())
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert results, "expected semantic results when embeddings are available"
    assert all(item["search_type"] in {"semantic", "basic"} for item in results)
    scores = [item["search_score"] for item in results]
    assert scores == sorted(scores, reverse=True)
    semantic_items = [item for item in results if item["search_type"] == "semantic"]
    if semantic_items:
        assert any("Cosine" in (item.get("rank_explanation") or "") for item in semantic_items)
    else:
        assert all((item.get("rank_explanation") or "").startswith("Basic search") for item in results)
    assert all(isinstance(item.get("score_components"), dict) for item in results)


def test_semantic_search_provider_disabled_fallback(monkeypatch):
    seed_memory_blocks()
    monkeypatch.setenv("EMBEDDING_PROVIDER", "disabled")
    reset_embedding_service_for_tests()

    r = client.get("/memory-blocks/search/semantic", params={"query": "retry logic"}, headers=auth())
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert results, "fallback search should still return results"
    assert all(item["search_type"] == "basic" for item in results)
    assert all("score_components" in item for item in results)


def test_hybrid_search():
    seed_memory_blocks()
    r = client.get("/memory-blocks/search/hybrid", params={"query": "database optimization"}, headers=auth())
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert results
    assert all("score_components" in item for item in results)
