import uuid

import pytest

from core.db import models
from core.services import (
    get_embedding_service,
    reset_embedding_service_for_tests,
)


@pytest.fixture(autouse=True)
def reset_embedding(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("EMBEDDING_DIMENSION", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACE_EMBEDDING_MODEL", raising=False)
    reset_embedding_service_for_tests()
    yield
    reset_embedding_service_for_tests()


def _memory_block(content: str = "Hello") -> models.MemoryBlock:
    return models.MemoryBlock(
        id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        content=content,
        lessons_learned="Lessons",
        metadata_col={"topic": "test"},
    )


def test_mock_provider_embedding(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "8")
    reset_embedding_service_for_tests()
    service = get_embedding_service()
    vector = service.embed_text("sample text")
    assert vector is not None
    assert len(vector) == 8


def test_attach_embedding(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "4")
    reset_embedding_service_for_tests()
    service = get_embedding_service()
    memory = _memory_block("Embedding content")
    service.attach_embedding(memory, save_empty=True)
    assert memory.content_embedding is not None
    assert len(memory.content_embedding) == 4


def test_disabled_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "disabled")
    reset_embedding_service_for_tests()
    service = get_embedding_service()
    memory = _memory_block("")
    service.attach_embedding(memory)
    assert memory.content_embedding is None


def test_embed_text_blank_returns_none(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    reset_embedding_service_for_tests()
    service = get_embedding_service()
    assert service.embed_text("   ") is None


def test_compose_memory_text(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "disabled")
    reset_embedding_service_for_tests()
    service = get_embedding_service()
    memory = _memory_block("Core content")
    memory.errors = "Boom"
    memory.metadata_col = {"b": 2, "a": 1}
    text = service.compose_memory_text(memory)
    assert "Core content" in text
    assert "Errors: Boom" in text
    assert '"a": 1' in text
