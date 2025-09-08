import uuid
from core.pruning.pruning_service import PruningService
from core.db.database import SessionLocal
from core.db import models


def seed_blocks(db):
    # create an agent to satisfy NOT NULL agent_id constraint
    agent = models.Agent(agent_name="PruneAgent", visibility_scope="personal")
    db.add(agent)
    db.commit()
    db.refresh(agent)
    for i in range(5):
        mb = models.MemoryBlock(
            content=f"block {i} content" + (" extra" * i),
            visibility_scope="personal",
            agent_id=agent.agent_id,
            conversation_id=uuid.uuid4(),
        )
        db.add(mb)
    db.commit()


def test_pruning_service_fallback_scoring():
    svc = PruningService(llm_api_key=None)  # force fallback
    with SessionLocal() as db:
        seed_blocks(db)
        suggestions = svc.generate_pruning_suggestions(db, batch_size=5)
        assert suggestions["suggestions"], "Expected pruning suggestions"
        first = suggestions["suggestions"][0]
        assert "pruning_score" in first
        assert 1 <= first["pruning_score"] <= 100


def test_pruning_service_random_blocks_no_error_on_empty():
    svc = PruningService(llm_api_key=None)
    with SessionLocal() as db:
        blocks = svc.get_random_memory_blocks(db, batch_size=3)
        # May be empty if no memory blocks yet
        assert isinstance(blocks, list)
