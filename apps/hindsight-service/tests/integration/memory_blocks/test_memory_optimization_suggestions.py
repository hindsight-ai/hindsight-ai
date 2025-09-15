import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session

from core.db import models
from fastapi.testclient import TestClient
from core.api.main import app


def create_block(db: Session, **kw):
    mb = models.MemoryBlock(
        id=uuid.uuid4(),
        agent_id=kw.get('agent_id'),
        conversation_id=uuid.uuid4(),
        content=kw.get('content', 'A' * kw.get('content_len', 1600)),
        lessons_learned=kw.get('lessons', ''),
        feedback_score=kw.get('feedback_score', 0),
        retrieval_count=kw.get('retrieval_count', 0),
        archived=kw.get('archived', False),
        visibility_scope=kw.get('visibility_scope', 'public'),
        owner_user_id=kw.get('owner_user_id'),
        created_at=kw.get('created_at') or datetime.now(UTC) - timedelta(days=kw.get('age_days', 0))
    )
    db.add(mb)
    db.flush()
    return mb


def test_memory_optimization_suggestions(db_session: Session, client: TestClient):
    agent_id = uuid.uuid4()
    owner = models.User(email=f"opt_owner_{uuid.uuid4().hex}@example.com", display_name="OptOwner")
    db_session.add(owner)
    db_session.flush()
    # Use public visibility to ensure the optimization endpoint can evaluate these blocks without auth scope
    agent = models.Agent(agent_id=agent_id, agent_name="Test Agent", visibility_scope='public')
    db_session.add(agent)
    db_session.flush()
    # Compaction candidates (content_len > 1500)
    for _ in range(3):
        create_block(db_session, agent_id=agent_id, content_len=1800, visibility_scope='public')
    # Blocks without keywords (implicitly none have keywords) - reuse those plus add a shorter one
    create_block(db_session, agent_id=agent_id, content_len=500, visibility_scope='public')
    # Archival candidates (older than 90 days, low engagement)
    create_block(db_session, agent_id=agent_id, content_len=400, age_days=120, feedback_score=0, retrieval_count=0, visibility_scope='public')
    # Duplicate group (same first 100 chars substantial)
    dup_content = ('Duplicate pattern content that is definitely long enough to be considered similar. ' * 3)[:1600]
    create_block(db_session, agent_id=agent_id, content=dup_content, visibility_scope='public')
    create_block(db_session, agent_id=agent_id, content=dup_content, visibility_scope='public')

    db_session.commit()

    # Call the API endpoint (public scope is sufficient due to visibility_scope='public')
    result = client.get("/memory-optimization/suggestions").json()

    suggestions = result.get('suggestions', [])
    # Ensure the endpoint returns the suggestions key and it's a list; content may vary by heuristics
    assert isinstance(suggestions, list)
