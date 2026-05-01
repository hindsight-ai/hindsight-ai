"""Gate tests for the E2E test-fixtures endpoints.

Verifies the security model documented in `core/api/test_fixtures.py`:
- When ``E2E_TEST_HOOKS`` env var is unset / false, every endpoint
  returns **404** (route appears not to exist).
- When set to "true", endpoints function normally.

These tests pin the gate behavior so a future refactor that accidentally
removes the `_assert_hooks_enabled()` check will fail loudly.
"""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from core.db import models


def _seed_user_and_block(db_session) -> tuple[models.User, models.MemoryBlock]:
    user = models.User(
        email=f"hooks-gate-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Hooks Gate User",
        beta_access_status="accepted",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    agent = models.Agent(
        agent_name=f"hooks-gate-agent-{uuid.uuid4().hex[:6]}",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    block = models.MemoryBlock(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="hooks gate test content",
        lessons_learned="hooks gate test lessons",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)
    return user, block


def _payload(block_id: uuid.UUID) -> dict:
    return {
        "suggested_content": "merged content",
        "suggested_lessons_learned": "merged lessons",
        "suggested_keywords": ["test"],
        "original_memory_ids": [str(block_id)],
    }


def _headers(user: models.User) -> dict:
    return {
        "x-auth-request-email": user.email,
        "x-auth-request-user": user.email,
    }


def test_seed_endpoint_returns_404_when_hooks_flag_unset(monkeypatch, db_session):
    """Default behavior: env var unset means /test-fixtures/* routes don't exist."""
    monkeypatch.delenv("E2E_TEST_HOOKS", raising=False)

    # The router is conditionally mounted in main.py at app construction
    # time; importing it would mount it. Bypass by directly invoking the
    # handler module's gate behavior — the in-handler check is the
    # defense-in-depth that we test here.
    from core.api import test_fixtures as tf

    assert tf._hooks_enabled() is False
    with pytest.raises(Exception) as exc_info:
        tf._assert_hooks_enabled()
    # FastAPI HTTPException raises with status_code 404
    assert getattr(exc_info.value, "status_code", None) == 404


def test_seed_endpoint_returns_404_when_hooks_flag_false(monkeypatch):
    """Explicit false also disables the routes."""
    monkeypatch.setenv("E2E_TEST_HOOKS", "false")
    from core.api import test_fixtures as tf

    assert tf._hooks_enabled() is False


def test_seed_endpoint_works_when_hooks_flag_true(monkeypatch, db_session):
    """With the flag set, the handler creates the suggestion row."""
    monkeypatch.setenv("E2E_TEST_HOOKS", "true")
    from core.api import test_fixtures as tf
    from core.api.main import app

    # The router is conditionally mounted at app startup. For this in-process
    # test we mount it explicitly to verify handler behavior.
    if not any(getattr(r, "path", "").startswith("/test-fixtures") for r in app.routes):
        app.include_router(tf.router)

    user, block = _seed_user_and_block(db_session)
    client = TestClient(app)
    resp = client.post(
        "/test-fixtures/consolidation-suggestion",
        json=_payload(block.id),
        headers=_headers(user),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "suggestion_id" in body
    assert body["status"] == "pending"


def test_seed_endpoint_rejects_block_owned_by_another_user(monkeypatch, db_session):
    """Defense against leaked-endpoint scenario: user can't seed against blocks they don't own."""
    monkeypatch.setenv("E2E_TEST_HOOKS", "true")
    from core.api import test_fixtures as tf
    from core.api.main import app

    if not any(getattr(r, "path", "").startswith("/test-fixtures") for r in app.routes):
        app.include_router(tf.router)

    owner, block = _seed_user_and_block(db_session)
    other_user = models.User(
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Other User",
        beta_access_status="accepted",
    )
    db_session.add(other_user)
    db_session.commit()

    client = TestClient(app)
    # `other_user` tries to seed a suggestion using `owner`'s block
    resp = client.post(
        "/test-fixtures/consolidation-suggestion",
        json=_payload(block.id),
        headers=_headers(other_user),
    )
    assert resp.status_code == 403, resp.text
    assert "not owned" in resp.text
