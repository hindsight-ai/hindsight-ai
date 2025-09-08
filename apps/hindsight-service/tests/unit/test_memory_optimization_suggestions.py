import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session

from core.db import models
from core.api.memory_optimization import get_memory_optimization_suggestions


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
        created_at=kw.get('created_at') or datetime.now(UTC) - timedelta(days=kw.get('age_days', 0))
    )
    db.add(mb)
    db.flush()
    return mb


def test_memory_optimization_suggestions(db_session: Session):
    agent_id = uuid.uuid4()
    agent = models.Agent(agent_id=agent_id, agent_name="Test Agent")
    db_session.add(agent)
    db_session.flush()
    # Compaction candidates (content_len > 1500)
    for _ in range(3):
        create_block(db_session, agent_id=agent_id, content_len=1800)
    # Blocks without keywords (implicitly none have keywords) - reuse those plus add a shorter one
    create_block(db_session, agent_id=agent_id, content_len=500)
    # Archival candidates (older than 90 days, low engagement)
    create_block(db_session, agent_id=agent_id, content_len=400, age_days=120, feedback_score=0, retrieval_count=0)
    # Duplicate group (same first 100 chars substantial)
    dup_content = ('Duplicate pattern content that is definitely long enough to be considered similar. ' * 3)[:1600]
    create_block(db_session, agent_id=agent_id, content=dup_content)
    create_block(db_session, agent_id=agent_id, content=dup_content)

    db_session.commit()

    import asyncio
    # Use asyncio.run for modern event loop management (avoids deprecated get_event_loop warning)
    result = asyncio.run(get_memory_optimization_suggestions(db_session))

    types = {s['type'] for s in result['suggestions']}
    assert 'compaction' in types
    assert 'keywords' in types
    assert 'archive' in types
    # merge may or may not appear depending on length heuristics
    assert any(s['type'] == 'merge' for s in result['suggestions'])
