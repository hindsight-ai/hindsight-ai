import uuid
from core.pruning.pruning_service import PruningService
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


def test_pruning_service_fallback_scoring(db_session):
    svc = PruningService(llm_api_key=None)  # force fallback
    seed_blocks(db_session)
    suggestions = svc.generate_pruning_suggestions(db_session, batch_size=5)
    assert suggestions["suggestions"], "Expected pruning suggestions"
    first = suggestions["suggestions"][0]
    assert "pruning_score" in first
    assert 1 <= first["pruning_score"] <= 100


def test_pruning_service_random_blocks_no_error_on_empty(db_session):
    svc = PruningService(llm_api_key=None)
    blocks = svc.get_random_memory_blocks(db_session, batch_size=3)
    # May be empty if no memory blocks yet
    assert isinstance(blocks, list)


def test_pruning_service_init():
    svc = PruningService("fake_key")
    assert svc.llm_api_key == "fake_key"


def test_pruning_service_init_no_key():
    import os
    old_key = os.environ.get('LLM_API_KEY')
    os.environ['LLM_API_KEY'] = 'env_key'
    try:
        svc = PruningService()
        assert svc.llm_api_key == 'env_key'
    finally:
        if old_key:
            os.environ['LLM_API_KEY'] = old_key
        else:
            os.environ.pop('LLM_API_KEY', None)


def test_evaluate_memory_blocks_with_llm_empty():
    svc = PruningService("fake_key")
    result = svc.evaluate_memory_blocks_with_llm([])
    assert result == []


def test_fallback_score_block():
    svc = PruningService("fake_key")
    block = {
        "id": "1",
        "content": "test content",
        "feedback_score": 5,
        "retrieval_count": 10,
        "created_at": "2023-01-01T00:00:00Z"
    }
    result = svc._fallback_score_block(block)
    assert "pruning_score" in result
    assert "pruning_rationale" in result
    assert 1 <= result["pruning_score"] <= 100
