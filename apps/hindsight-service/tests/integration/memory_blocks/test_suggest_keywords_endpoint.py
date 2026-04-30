"""Regression test for #82 — POST /memory-blocks/{id}/suggest-keywords.

Pre-#82 the dashboard's `memoryService.suggestKeywords` POSTed to this
URL but no backend endpoint existed → 404. Post-#82 the endpoint uses
the canonical `core.services.keyword_extraction_service.extract_keywords`
function (same one the bulk flow uses), so per-block and bulk paths
cannot diverge.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models


def _headers(email: str):
    return {
        "x-auth-request-email": email,
        "x-auth-request-user": email.split("@")[0],
        "x-active-scope": "personal",
    }


def test_suggest_keywords_endpoint_returns_keywords(db_session):
    """Owner posts to /memory-blocks/{id}/suggest-keywords → 200 + keywords list."""
    user = models.User(
        email=f"sk-{uuid.uuid4().hex[:8]}@example.com",
        display_name="SK User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    agent = models.Agent(
        agent_name=f"sk-agent-{uuid.uuid4().hex[:6]}",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    mb = models.MemoryBlock(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="Python FastAPI database optimization with PostgreSQL and Redis caching for high performance",
        lessons_learned="Use connection pooling and indexed queries for the API endpoints.",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    db_session.add(mb)
    db_session.commit()
    db_session.refresh(mb)

    client = TestClient(app)
    resp = client.post(
        f"/memory-blocks/{mb.id}/suggest-keywords",
        headers=_headers(user.email),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["memory_block_id"] == str(mb.id)
    assert isinstance(data["suggested_keywords"], list)
    # Should pick up at least one technical term given the content
    assert len(data["suggested_keywords"]) > 0, (
        f"Expected at least one suggested keyword from technical content; "
        f"got {data['suggested_keywords']!r}"
    )
    assert "current_keywords" in data


def test_suggest_keywords_endpoint_404_for_missing_block(db_session):
    """Non-existent memory_id should return 404 (not the pre-#82 endpoint-missing 404)."""
    user = models.User(
        email=f"sk-404-{uuid.uuid4().hex[:8]}@example.com",
        display_name="SK 404",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    client = TestClient(app)
    fake_id = uuid.uuid4()
    resp = client.post(
        f"/memory-blocks/{fake_id}/suggest-keywords",
        headers=_headers(user.email),
    )
    assert resp.status_code == 404, resp.text
    assert "Memory block not found" in resp.text


def test_keyword_extraction_canonical_alias_preserved():
    """Pre-#82 callers used `extract_keywords_enhanced`; the alias must stay."""
    from core.services.keyword_extraction_service import (
        extract_keywords,
        extract_keywords_enhanced,
    )
    assert extract_keywords is extract_keywords_enhanced, (
        "extract_keywords_enhanced must remain an alias for extract_keywords "
        "to preserve backward-compat with existing callers (memory_optimization.py, "
        "memory_blocks_bulk.py, and pre-#82 test patches)."
    )

    # Sanity: function works.
    out = extract_keywords("Python FastAPI database optimization", max_keywords=5)
    assert isinstance(out, list)
    assert all(isinstance(kw, str) for kw in out)
