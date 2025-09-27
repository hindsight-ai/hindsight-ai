import pytest
from fastapi.testclient import TestClient

from core.api.main import app
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
    agent_resp = client.post(
        "/agents/",
        json={"agent_name": "SearchAgent", "visibility_scope": "personal"},
        headers=auth(),
    )
    assert agent_resp.status_code == 201, agent_resp.text
    agent_id = agent_resp.json()["agent_id"]

    import uuid as _uuid

    texts = [
        "Alpha project planning meeting notes about database optimization.",
        "Beta release retrospective covering performance and logging.",
        "Gamma incident report detailing error handling and retry logic.",
    ]
    ids = []
    for text in texts:
        response = client.post(
            "/memory-blocks/",
            json={
                "content": text,
                "visibility_scope": "personal",
                "agent_id": agent_id,
                "conversation_id": str(_uuid.uuid4()),
            },
            headers=auth(),
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    return ids


def test_fulltext_search_basic():
    seed_memory_blocks()
    response = client.get(
        "/memory-blocks/search/fulltext",
        params={"query": "performance"},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)


def test_semantic_search_returns_scored_results():
    seed_memory_blocks()
    response = client.get(
        "/memory-blocks/search/semantic",
        params={"query": "retry logic"},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)
    assert results, "expected results when embeddings are available"
    search_types = {item["search_type"] for item in results}
    assert search_types <= {"semantic", "basic"}
    scores = [item["search_score"] for item in results]
    assert scores == sorted(scores, reverse=True)
    if "semantic" in search_types:
        assert any("Cosine" in (item.get("rank_explanation") or "") for item in results)


def test_semantic_search_provider_disabled_fallback(monkeypatch):
    seed_memory_blocks()
    monkeypatch.setenv("EMBEDDING_PROVIDER", "disabled")
    reset_embedding_service_for_tests()

    response = client.get(
        "/memory-blocks/search/semantic",
        params={"query": "retry logic"},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)
    assert results, "fallback search should still return results"
    assert all(item["search_type"] == "basic" for item in results)


def test_hybrid_search():
    seed_memory_blocks()
    response = client.get(
        "/memory-blocks/search/hybrid",
        params={"query": "database optimization"},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)
    assert results
