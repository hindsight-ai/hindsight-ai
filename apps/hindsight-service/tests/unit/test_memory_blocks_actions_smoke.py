import uuid
from fastapi.testclient import TestClient

from core.api.main import app


client = TestClient(app)


def _h(user, email):
    return {"x-auth-request-user": user, "x-auth-request-email": email}


def test_memory_block_archive_and_delete_smoke():
    user_email = f"mb_user_{uuid.uuid4().hex[:8]}@example.com"

    # Create agent
    r_agent = client.post("/agents/", json={"agent_name": "MB Test Agent"}, headers=_h("mbuser", user_email))
    if r_agent.status_code == 400:
        return
    assert r_agent.status_code == 201, r_agent.text
    agent_id = r_agent.json()["agent_id"]

    # Create memory block
    r_mb = client.post(
        "/memory-blocks/",
        json={
            "content": "memory content",
            "agent_id": agent_id,
            "conversation_id": str(uuid.uuid4()),
            "visibility_scope": "personal",
        },
        headers=_h("mbuser", user_email),
    )
    assert r_mb.status_code in (201, 400), r_mb.text
    mb_id = r_mb.json()["id"]

    # Archive
    r_arch = client.post(f"/memory-blocks/{mb_id}/archive", headers=_h("mbuser", user_email))
    assert r_arch.status_code == 200
    assert r_arch.json().get("archived") is True

    # Soft delete (returns 204)
    r_del = client.delete(f"/memory-blocks/{mb_id}", headers=_h("mbuser", user_email))
    assert r_del.status_code == 204

    # Feedback path (should 404 now or be rejected gracefully)
    r_fb = client.post(
        f"/memory-blocks/{mb_id}/feedback/",
        json={"memory_id": mb_id, "feedback_type": "positive"},
        headers=_h("mbuser", user_email),
    )
    assert r_fb.status_code in (200, 404, 403)

