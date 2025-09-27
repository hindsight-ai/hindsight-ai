from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.services import embedding_service


@pytest.fixture(scope="session")
def _test_postgres():
    return "postgresql://mock:mock@localhost/mock"


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    yield


@pytest.fixture(autouse=True)
def db_session():
    yield None


def test_embedding_config_ollama_defaults(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    cfg = embedding_service.EmbeddingConfig.from_env()
    assert cfg.provider == "ollama"
    assert cfg.model == "nomic-embed-text:v1.5"
    assert cfg.base_url == "http://localhost:11434"


def test_ollama_embedding_provider_fallback_between_endpoints(monkeypatch):
    provider = embedding_service.OllamaEmbeddingProvider(
        model="fake-model",
        base_url="http://ollama:11434",
    )

    called = []

    def fake_post(url, json=None, timeout=None):  # pylint: disable=redefined-outer-name
        called.append(url)
        if url.endswith("/api/embeddings"):
            response = SimpleNamespace(status_code=404)
            response.raise_for_status = MagicMock(side_effect=embedding_service.requests.HTTPError("not found"))
            response.json = MagicMock(return_value={})
            return response
        else:
            data = {"embedding": [1.0, 0.0, -1.0]}
            response = SimpleNamespace(status_code=200)
            response.raise_for_status = MagicMock()
            response.json = MagicMock(return_value=data)
            return response

    monkeypatch.setattr(embedding_service.requests, "post", fake_post)

    vector = provider.embed("hello world")

    assert vector == [1.0, 0.0, -1.0]
    assert called == ["http://ollama:11434/api/embeddings", "http://ollama:11434/api/embed"]


def test_ollama_embedding_provider_rejects_invalid_payload(monkeypatch):
    provider = embedding_service.OllamaEmbeddingProvider(
        model="fake",
        base_url="http://ollama:11434",
    )

    def fake_post(url, json=None, timeout=None):
        response = SimpleNamespace(status_code=200)
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value={"unexpected": "data"})
        return response

    monkeypatch.setattr(embedding_service.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        provider.embed("oops")


def test_embedding_service_builds_mock_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    svc = embedding_service.EmbeddingService(embedding_service.EmbeddingConfig.from_env())
    assert svc.is_enabled
    vec = svc.embed_text("test")
    assert isinstance(vec, list)
    assert len(vec) == 32
    assert all(isinstance(x, float) for x in vec)
