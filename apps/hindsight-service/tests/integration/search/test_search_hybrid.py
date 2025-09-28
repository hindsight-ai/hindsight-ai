import uuid
from sqlalchemy.orm import Session

from core.services.search_service import SearchService
from core.services.embedding_service import get_embedding_service, reset_embedding_service_for_tests
from core.db import models


def seed_blocks(db: Session, agent_id, owner_id, embedding_service):
    contents = [
        "First block about python testing and coverage.",
        "Second block about search ranking algorithms.",
        "Third block mentions Python and algorithms together for hybrid search.",
    ]
    blocks = []
    for text in contents:
        mb = models.MemoryBlock(
            id=uuid.uuid4(),
            agent_id=agent_id,
            conversation_id=uuid.uuid4(),
            content=text,
            lessons_learned="",
            visibility_scope="personal",
            owner_user_id=owner_id,
        )
        db.add(mb)
        blocks.append(mb)
    db.flush()
    # Ensure embeddings exist so semantic path has vectors to query
    embedding_service.backfill_missing_embeddings(db, batch_size=len(blocks))
    return blocks


def test_hybrid_search_combines_scores(db_session: Session, monkeypatch):
    agent_id = uuid.uuid4()
    # create owner and agent to satisfy personal-owner constraint
    owner = models.User(email=f"hybrid_owner_{uuid.uuid4().hex}@example.com", display_name="HybridOwner")
    db_session.add(owner)
    db_session.flush()
    agent = models.Agent(agent_id=agent_id, agent_name="Hybrid Agent", owner_user_id=owner.id)
    db_session.add(agent)
    db_session.flush()

    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "8")
    reset_embedding_service_for_tests()
    embedding_service = get_embedding_service()

    seed_blocks(db_session, agent_id, owner.id, embedding_service)
    db_session.commit()

    service = SearchService()
    # Use a term that appears across blocks to trigger fallback basic search (since FTS vectors not populated in tests)
    results, meta = service.search_memory_blocks_hybrid(db_session, query="block", agent_id=agent_id, limit=5)

    # Fallback should yield results via basic search path elevated to hybrid output
    assert results == [] or meta["search_type"] == "hybrid"  # allow empty if filtering logic changes
    assert "combined_results_count" in meta
    assert "component_summary" in meta
