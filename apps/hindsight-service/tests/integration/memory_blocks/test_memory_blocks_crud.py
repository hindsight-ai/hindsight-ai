import uuid
from core.db import models, crud, schemas


def test_create_memory_block_with_keywords(monkeypatch, db_session):
    db = db_session
    owner = models.User(email=f"mem_{uuid.uuid4().hex}@ex.com", display_name="MemUser", is_superadmin=False)
    db.add(owner); db.commit(); db.refresh(owner)
    agent = models.Agent(agent_name=f"MemAgent {uuid.uuid4().hex[:5]}", visibility_scope="personal", owner_user_id=owner.id)
    db.add(agent); db.commit(); db.refresh(agent)

    # Stub keyword extractor to return deterministic set
    def fake_extract(text):
        return ["alpha", "beta", "alpha"]  # duplicate to test set logic
    # Patch the simple heuristic extractor
    monkeypatch.setattr("core.utils.keywords.simple_extract_keywords", fake_extract)

    payload = schemas.MemoryBlockCreate(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="Some content about Alpha and Beta",
        errors=None,
        lessons_learned="LL",
        metadata_col={"x": 1},
        visibility_scope="personal",
        owner_user_id=owner.id,
    )
    mb = crud.create_memory_block(db, payload)
    # Returned schema
    assert mb.agent_id == agent.agent_id
    # Verify keyword associations persisted
    kw_texts = {k.keyword_text for k in db.query(models.Keyword).all()}
    assert {"alpha", "beta"}.issubset(kw_texts)
    # Feedback log created
    logs = db.query(models.FeedbackLog).filter(models.FeedbackLog.memory_id == mb.id).all()
    assert len(logs) == 1
