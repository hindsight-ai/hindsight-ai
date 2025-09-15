import uuid
from datetime import datetime, timezone
from core.db import models, crud, schemas


def _seed_memory_block(db, content="Base Content"):
    user = models.User(email=f"cuser_{uuid.uuid4().hex}@ex.com", display_name="CU", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)
    agent = models.Agent(agent_name=f"CAgent {uuid.uuid4().hex[:5]}", visibility_scope="personal", owner_user_id=user.id)
    db.add(agent); db.commit(); db.refresh(agent)
    mb = models.MemoryBlock(agent_id=agent.agent_id, conversation_id=uuid.uuid4(), content=content, lessons_learned="LL", visibility_scope="personal", owner_user_id=user.id)
    db.add(mb); db.commit(); db.refresh(mb)
    return mb, agent


def test_consolidation_full_flow(db_session):
    db = db_session
    mb1, agent = _seed_memory_block(db, "First piece")
    mb2, _ = _seed_memory_block(db, "Second piece")

    group_id = uuid.uuid4()
    create_payload = schemas.ConsolidationSuggestionCreate(
        group_id=group_id,
        suggested_content="Unified content",
        suggested_lessons_learned="Unified lessons",
        suggested_keywords=["merge", "unify"],
        original_memory_ids=[str(mb1.id), str(mb2.id)],
        status="pending",
    )
    suggestion = crud.create_consolidation_suggestion(db, create_payload)
    assert suggestion.status == "pending"

    # List with status filter
    suggestions, total = crud.get_consolidation_suggestions(db, status="pending")
    assert total == 1 and suggestions[0].suggestion_id == suggestion.suggestion_id

    # Update status
    upd = schemas.ConsolidationSuggestionUpdate(status="pending")  # no-op but exercise path
    updated = crud.update_consolidation_suggestion(db, suggestion.suggestion_id, upd)
    assert updated.status == "pending"

    # Apply consolidation (archives originals & creates new block)
    new_block = crud.apply_consolidation(db, suggestion.suggestion_id)
    assert new_block is not None
    assert new_block.content == "Unified content"
    # Originals archived
    orig1 = crud.get_memory_block(db, mb1.id)
    orig2 = crud.get_memory_block(db, mb2.id)
    assert orig1.archived and orig2.archived

    # Re-applying returns None (status no longer pending)
    assert crud.apply_consolidation(db, suggestion.suggestion_id) is None

    # Delete suggestion (should succeed)
    assert crud.delete_consolidation_suggestion(db, suggestion.suggestion_id) is True
    # Deleting again is False
    assert crud.delete_consolidation_suggestion(db, suggestion.suggestion_id) is False
