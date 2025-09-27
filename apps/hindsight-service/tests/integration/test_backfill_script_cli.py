from __future__ import annotations

import runpy
import uuid
from pathlib import Path

import pytest

from core.db import database, models, schemas
from core.db.repositories import memory_blocks as repo_memory_blocks
from core.services.embedding_service import reset_embedding_service_for_tests


SCRIPT_GLOBALS = runpy.run_path(
    Path(__file__).resolve().parents[2] / "scripts" / "backfill_embeddings.py"
)
MAIN = SCRIPT_GLOBALS["main"]


def _create_user_and_agent(session):
    user = models.User(
        email=f"backfill-cli-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Backfill CLI Tester",
        is_superadmin=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    agent = models.Agent(
        agent_id=uuid.uuid4(),
        agent_name=f"BackfillAgent-{uuid.uuid4().hex[:6]}",
        visibility_scope="personal",
        owner_user_id=user.id,
        organization_id=None,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return user, agent


def _seed_memory_without_embedding() -> uuid.UUID:
    session = database.SessionLocal()
    try:
        user, agent = _create_user_and_agent(session)
        payload = schemas.MemoryBlockCreate(
            agent_id=agent.agent_id,
            conversation_id=uuid.uuid4(),
            content="CLI backfill target",
            visibility_scope="personal",
            owner_user_id=user.id,
        )
        block = repo_memory_blocks.create_memory_block(session, payload)
        # Reload to ensure embedding missing
        stored = (
            session.query(models.MemoryBlock)
            .filter(models.MemoryBlock.id == block.id)
            .one()
        )
        assert stored.content_embedding is None
        return stored.id
    finally:
        session.close()


def _cleanup_records(memory_id):
    session = database.SessionLocal()
    try:
        block = (
            session.query(models.MemoryBlock)
            .filter(models.MemoryBlock.id == memory_id)
            .one_or_none()
        )
        if block is not None:
            session.delete(block)
        session.commit()
    finally:
        session.close()


@pytest.mark.integration
def test_backfill_script_cli_populates_embeddings(monkeypatch, capsys):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "disabled")
    monkeypatch.delenv("EMBEDDING_DIMENSION", raising=False)
    reset_embedding_service_for_tests()

    memory_id = _seed_memory_without_embedding()

    try:
        monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
        monkeypatch.setenv("EMBEDDING_DIMENSION", "7")
        reset_embedding_service_for_tests()

        exit_code = MAIN(["--batch-size", "2"])
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Backfilled embeddings" in captured.out

        session = database.SessionLocal()
        try:
            stored = (
                session.query(models.MemoryBlock)
                .filter(models.MemoryBlock.id == memory_id)
                .one()
            )
            assert stored.content_embedding is not None
            assert len(stored.content_embedding or []) == 7
        finally:
            session.close()
    finally:
        _cleanup_records(memory_id)
        reset_embedding_service_for_tests()
