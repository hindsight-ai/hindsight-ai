import uuid

import pytest

from core.db import models, schemas, crud
from core.services.embedding_service import get_embedding_service, reset_embedding_service_for_tests


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


def _make_agent(db, scope="personal"):
    owner = models.User(
        email=f"embedding_{uuid.uuid4().hex[:6]}@example.com",
        display_name="Embedding Tester",
        is_superadmin=False,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    agent = models.Agent(
        agent_id=uuid.uuid4(),
        agent_name=f"EmbeddingAgent-{uuid.uuid4().hex[:6]}",
        visibility_scope=scope,
        owner_user_id=owner.id if scope == "personal" else None,
        organization_id=None,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent, owner


def test_embeddings_generated_on_create(monkeypatch, db_session):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "5")
    reset_embedding_service_for_tests()

    db = db_session
    agent, owner = _make_agent(db)
    payload = schemas.MemoryBlockCreate(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="Embedding enabled memory",
        visibility_scope="personal",
        owner_user_id=owner.id,
    )
    block = crud.create_memory_block(db, payload)
    assert block.content_embedding is not None
    assert len(block.content_embedding or []) == 5

    stored = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == block.id).first()
    assert stored is not None
    assert stored.content_embedding is not None


def test_backfill_missing_embeddings(monkeypatch, db_session):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "disabled")
    reset_embedding_service_for_tests()
    db = db_session
    agent, owner = _make_agent(db)
    payload = schemas.MemoryBlockCreate(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="Backfill target",
        visibility_scope="personal",
        owner_user_id=owner.id,
    )
    block = crud.create_memory_block(db, payload)
    stored = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == block.id).first()
    assert stored is not None
    assert stored.content_embedding is None

    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "6")
    reset_embedding_service_for_tests()
    service = get_embedding_service()
    updated = service.backfill_missing_embeddings(db, batch_size=1)
    assert updated >= 1

    db.refresh(stored)
    assert stored.content_embedding is not None
    assert len(stored.content_embedding or []) == 6
