import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _headers(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com", "x-active-scope": "personal"}


def test_memory_block_create_requires_agent():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _headers("user")
    # Try to create memory block without agent
    r = client.post("/memory-blocks/", json={"content": "test content", "conversation_id": str(uuid.uuid4())}, headers=h)
    # API requires agent_id and returns 422 for validation or 404 if agent lookup fails; accept either
    assert r.status_code in (404, 422)


def test_memory_block_update():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _headers("user")
    # Create agent first
    r = client.post("/agents/", json={"agent_name": "MemBlockAgent", "description": "for memory blocks"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Create memory block
    r2 = client.post("/memory-blocks/", json={"content": "original content", "agent_id": agent_id, "conversation_id": str(uuid.uuid4())}, headers=h)
    assert r2.status_code == 201
    block_id = r2.json()["id"]
    # Update memory block
    r3 = client.put(f"/memory-blocks/{block_id}", json={"content": "updated content"}, headers=h)
    assert r3.status_code == 200
    assert r3.json()["content"] == "updated content"


def test_crud_create_and_get_memory_block(db_session):
    from core.db import models, crud
    db = db_session
    # Create user and agent
    user = models.User(email="mem_test@example.com", display_name="MemTest", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)
    agent = models.Agent(agent_name="MemTestAgent", visibility_scope="personal", owner_user_id=user.id)
    db.add(agent); db.commit(); db.refresh(agent)
    # Create memory block
    block = models.MemoryBlock(
        content="test content",
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        visibility_scope="personal",
        owner_user_id=user.id
    )
    db.add(block); db.commit(); db.refresh(block)
    # Get memory block
    fetched = crud.get_memory_block(db, block.id)
    assert fetched.id == block.id
    assert fetched.content == "test content"


def test_memory_block_get_single():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _headers("user")
    # Create agent first
    r = client.post("/agents/", json={"agent_name": "SingleMemAgent", "description": "for single memory block"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Create memory block
    r2 = client.post("/memory-blocks/", json={"content": "single test content", "agent_id": agent_id, "conversation_id": str(uuid.uuid4())}, headers=h)
    assert r2.status_code == 201
    block_id = r2.json()["id"]
    # Get single memory block
    r3 = client.get(f"/memory-blocks/{block_id}", headers=h)
    assert r3.status_code == 200
    assert r3.json()["id"] == block_id


def test_memory_block_update_2():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _headers("user")
    # Create agent first
    r = client.post("/agents/", json={"agent_name": "UpdateMemAgent", "description": "for memory block update"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Create memory block
    r2 = client.post("/memory-blocks/", json={"content": "original content 2", "agent_id": agent_id, "conversation_id": str(uuid.uuid4())}, headers=h)
    assert r2.status_code == 201
    block_id = r2.json()["id"]
    # Update memory block
    r3 = client.put(f"/memory-blocks/{block_id}", json={"content": "updated content 2"}, headers=h)
    assert r3.status_code == 200
    assert r3.json()["content"] == "updated content 2"


def test_memory_block_archive():
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _headers("user")
    # Create agent first
    r = client.post("/agents/", json={"agent_name": "ArchiveMemAgent", "description": "for memory block archive"}, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    # Create memory block
    r2 = client.post("/memory-blocks/", json={"content": "content to archive", "agent_id": agent_id, "conversation_id": str(uuid.uuid4())}, headers=h)
    assert r2.status_code == 201
    block_id = r2.json()["id"]
    # Archive memory block
    r3 = client.delete(f"/memory-blocks/{block_id}", headers=h)
    assert r3.status_code == 204
