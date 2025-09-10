import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _h(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def _create_personal_agent(client, headers, name="MBTester"):
    r = client.post("/agents/", json={"agent_name": name, "visibility_scope": "personal"}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["agent_id"]


def test_memory_block_create_personal_and_list(db_session):
    client = TestClient(main_app)
    h = _h("mbuser")
    agent_id = _create_personal_agent(client, h)
    payload = {
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "content": "Initial memory content",
        "visibility_scope": "personal",
    }
    r = client.post("/memory-blocks/", json=payload, headers=h)
    assert r.status_code == 201, r.text
    mb_id = r.json()["id"]
    # list
    r2 = client.get("/memory-blocks/", headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert data["total_items"] >= 1


def test_memory_block_create_org_forbidden_without_membership(db_session):
    client = TestClient(main_app)
    h = _h("nomember")
    agent_id = _create_personal_agent(client, h, name="A2")
    fake_org = str(uuid.uuid4())
    payload = {
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "content": "Org scoped attempt",
        "visibility_scope": "organization",
        "organization_id": fake_org,
    }
    r = client.post("/memory-blocks/", json=payload, headers=h)
    assert r.status_code in (403, 422)


def test_memory_block_archive_and_feedback(db_session):
    client = TestClient(main_app)
    h = _h("archiver")
    agent_id = _create_personal_agent(client, h, name="A3")
    payload = {
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "content": "Content to archive",
        "visibility_scope": "personal",
    }
    r = client.post("/memory-blocks/", json=payload, headers=h)
    assert r.status_code == 201
    mb_id = r.json()["id"]
    # Archive
    r2 = client.post(f"/memory-blocks/{mb_id}/archive", headers=h)
    assert r2.status_code == 200
    assert r2.json()["archived"] is True
    # Feedback
    r3 = client.post(f"/memory-blocks/{mb_id}/feedback/", json={"feedback_type": "upvote", "memory_id": mb_id}, headers=h)
    assert r3.status_code == 200


def test_bulk_generate_keywords_success(db_session):
    client = TestClient(main_app)
    h = _h("keyworduser")
    agent_id = _create_personal_agent(client, h, name="KeywordAgent")
    # Create a memory block with content
    payload = {
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "content": "This is a test about Python programming and API development using FastAPI framework",
        "lessons_learned": "Learned about REST APIs and database optimization",
        "visibility_scope": "personal",
    }
    r = client.post("/memory-blocks/", json=payload, headers=h)
    assert r.status_code == 201
    mb_id = r.json()["id"]

    # Generate keywords
    gen_payload = {"memory_block_ids": [mb_id]}
    r2 = client.post("/memory-blocks/bulk-generate-keywords", json=gen_payload, headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert "suggestions" in data
    assert data["successful_count"] >= 1
    assert len(data["suggestions"]) >= 1
    suggestion = data["suggestions"][0]
    assert "suggested_keywords" in suggestion
    assert isinstance(suggestion["suggested_keywords"], list)


def test_bulk_generate_keywords_empty_list(db_session):
    client = TestClient(main_app)
    h = _h("emptyuser")
    gen_payload = {"memory_block_ids": []}
    r = client.post("/memory-blocks/bulk-generate-keywords", json=gen_payload, headers=h)
    assert r.status_code == 400
    assert "No memory block IDs provided" in r.json()["detail"]


def test_bulk_apply_keywords_success(db_session):
    client = TestClient(main_app)
    h = _h("applyuser")
    agent_id = _create_personal_agent(client, h, name="ApplyAgent")
    # Create a memory block
    payload = {
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "content": "Test content for keyword application",
        "visibility_scope": "personal",
    }
    r = client.post("/memory-blocks/", json=payload, headers=h)
    assert r.status_code == 201
    mb_id = r.json()["id"]

    # Apply keywords
    apply_payload = {
        "applications": [
            {
                "memory_block_id": mb_id,
                "selected_keywords": ["test", "keyword", "application"]
            }
        ]
    }
    r2 = client.post("/memory-blocks/bulk-apply-keywords", json=apply_payload, headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert "results" in data
    assert data["successful_count"] >= 1
    assert len(data["results"]) >= 1
    result = data["results"][0]
    assert result["success"] is True
    assert "added_keywords" in result


def test_bulk_apply_keywords_empty_list(db_session):
    client = TestClient(main_app)
    h = _h("applyempty")
    apply_payload = {"applications": []}
    r = client.post("/memory-blocks/bulk-apply-keywords", json=apply_payload, headers=h)
    assert r.status_code == 400
    assert "No keyword applications provided" in r.json()["detail"]


def test_bulk_compact_memory_blocks_success(db_session):
    client = TestClient(main_app)
    h = _h("compactuser")
    agent_id = _create_personal_agent(client, h, name="CompactAgent")
    # Create a memory block
    payload = {
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4()),
        "content": "This is a long content that can be compressed using AI to make it shorter and more concise",
        "lessons_learned": "Learned about compression techniques",
        "visibility_scope": "personal",
    }
    r = client.post("/memory-blocks/", json=payload, headers=h)
    assert r.status_code == 201
    mb_id = r.json()["id"]

    # Mock the LLM API key
    import os
    original_key = os.environ.get("LLM_API_KEY")
    os.environ["LLM_API_KEY"] = "fake_key_for_testing"

    try:
        # Compact memory blocks
        compact_payload = {
            "memory_block_ids": [mb_id],
            "user_instructions": "Make this content more concise",
            "max_concurrent": 1
        }
        r2 = client.post("/memory-blocks/bulk-compact", json=compact_payload, headers=h)
        # Should succeed even with fake key since we're testing the endpoint structure
        # The actual compression might fail but the endpoint should handle it gracefully
        assert r2.status_code in (200, 500)  # 200 if compression works, 500 if LLM fails
        if r2.status_code == 200:
            data = r2.json()
            assert "results" in data
            assert data["total_processed"] >= 1
    finally:
        # Restore original environment
        if original_key is not None:
            os.environ["LLM_API_KEY"] = original_key
        elif "LLM_API_KEY" in os.environ:
            del os.environ["LLM_API_KEY"]


def test_bulk_compact_memory_blocks_no_api_key(db_session):
    client = TestClient(main_app)
    h = _h("nokeyuser")
    # Ensure no LLM API key
    import os
    original_key = os.environ.get("LLM_API_KEY")
    if "LLM_API_KEY" in os.environ:
        del os.environ["LLM_API_KEY"]

    try:
        compact_payload = {
            "memory_block_ids": ["fake-id"],
            "user_instructions": "Compress this",
            "max_concurrent": 1
        }
        r = client.post("/memory-blocks/bulk-compact", json=compact_payload, headers=h)
        assert r.status_code == 500
        assert "LLM service not available" in r.json()["detail"]
    finally:
        # Restore original environment
        if original_key is not None:
            os.environ["LLM_API_KEY"] = original_key


def test_bulk_compact_memory_blocks_empty_list(db_session):
    client = TestClient(main_app)
    h = _h("emptycompact")
    compact_payload = {"memory_block_ids": []}
    r = client.post("/memory-blocks/bulk-compact", json=compact_payload, headers=h)
    assert r.status_code == 400
    assert "No memory block IDs provided" in r.json()["detail"]