import uuid

from sqlalchemy.orm import Session

from core.db import models


def _headers(email: str) -> dict[str, str]:
    return {
        "X-Auth-Request-User": email.split("@")[0],
        "X-Auth-Request-Email": email,
        "X-Active-Scope": "personal",
    }


def test_delete_agent_cascades_feedback_logs_for_memory_blocks(client, db_session: Session):
    email = f"cascade_{uuid.uuid4().hex}@example.com"
    user = models.User(email=email, display_name="Cascade Owner")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    agent = models.Agent(
        agent_name=f"Cascade Agent {uuid.uuid4().hex}",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    memory_block = models.MemoryBlock(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="memory with feedback",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    db_session.add(memory_block)
    db_session.flush()

    db_session.add(
        models.FeedbackLog(
            memory_id=memory_block.id,
            feedback_type="positive",
            feedback_details="kept until the parent memory is deleted",
        )
    )
    db_session.commit()
    agent_id = agent.agent_id
    memory_id = memory_block.id

    response = client.delete(f"/agents/{agent_id}", headers=_headers(email))

    assert response.status_code == 204, response.text
    assert db_session.query(models.Agent).filter_by(agent_id=agent_id).count() == 0
    assert db_session.query(models.MemoryBlock).filter_by(id=memory_id).count() == 0
    assert db_session.query(models.FeedbackLog).filter_by(memory_id=memory_id).count() == 0
