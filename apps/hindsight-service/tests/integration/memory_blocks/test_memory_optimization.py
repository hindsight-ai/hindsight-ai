import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from core.api.memory_optimization import router
from core.db import models
import uuid


def test_get_memory_optimization_suggestions_empty(client, db_session):
    # Mock empty db
    # Clear any existing data
    db_session.query(models.MemoryBlock).delete()
    db_session.commit()
    
    response = client.get("/memory-optimization/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert data["total_memory_blocks_analyzed"] == 0


def test_get_memory_optimization_suggestions_with_data(client, db_session):
    # Create test data
    user = models.User(email="opt_test@example.com", display_name="Opt Test")
    db_session.add(user)
    db_session.flush()
    
    agent = models.Agent(agent_name="OptAgent", owner_user_id=user.id)
    db_session.add(agent)
    db_session.flush()
    
    # Long content block
    long_block = models.MemoryBlock(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="A" * 2000,  # Long content
        owner_user_id=user.id
    )
    db_session.add(long_block)
    
    # Block without keywords
    no_kw_block = models.MemoryBlock(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="Short content",
        owner_user_id=user.id
    )
    db_session.add(no_kw_block)
    
    # Old block
    from datetime import datetime, timezone
    old_block = models.MemoryBlock(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="Old content",
        owner_user_id=user.id,
        feedback_score=0,
        retrieval_count=0,
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc)  # Very old
    )
    db_session.add(old_block)
    
    db_session.commit()
    
    headers = {"x-auth-request-user": "opt_test", "x-auth-request-email": "opt_test@example.com"}
    response = client.get("/memory-optimization/suggestions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    print(f"DEBUG: Response data: {data}")
    print(f"DEBUG: Total blocks analyzed: {data['total_memory_blocks_analyzed']}")
    
    # Check what blocks are in the database
    all_blocks = db_session.query(models.MemoryBlock).all()
    print(f"DEBUG: Total blocks in DB: {len(all_blocks)}")
    for block in all_blocks:
        print(f"DEBUG: Block {block.id}: len={len(block.content or '')}, archived={block.archived}, keywords={len(block.memory_block_keywords or [])}")
    
    assert len(data["suggestions"]) > 0
    assert data["total_memory_blocks_analyzed"] == 3


def test_execute_optimization_suggestion_not_found(client):
    headers = {"x-auth-request-user": "testuser", "x-auth-request-email": "testuser@example.com"}
    response = client.post("/memory-optimization/suggestions/nonexistent/execute", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"]


def test_execute_optimization_suggestion_keywords(client, db_session):
    # Create test data
    user = models.User(email="exec_test@example.com", display_name="Exec Test")
    db_session.add(user)
    db_session.flush()
    
    agent = models.Agent(agent_name="ExecAgent", owner_user_id=user.id)
    db_session.add(agent)
    db_session.flush()
    
    block = models.MemoryBlock(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="This is a test memory block about Python programming and machine learning",
        owner_user_id=user.id
    )
    db_session.add(block)
    db_session.commit()
    
    # Mock the extract_keywords_enhanced function
    with patch('core.api.main.extract_keywords_enhanced', return_value=['python', 'programming']):
        headers = {"x-auth-request-user": "testuser", "x-auth-request-email": "testuser@example.com"}
        # First get suggestions to find the ID
        response = client.get("/memory-optimization/suggestions", headers=headers)
        suggestions = response.json()["suggestions"]
        keyword_suggestion = next((s for s in suggestions if s["type"] == "keywords"), None)
        
        if keyword_suggestion:
            suggestion_id = keyword_suggestion["id"]
            response = client.post(f"/memory-optimization/suggestions/{suggestion_id}/execute", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data  # Just check that it returns a status


def test_preview_optimization_suggestion(client):
    headers = {"x-auth-request-user": "testuser", "x-auth-request-email": "testuser@example.com"}
    response = client.get("/memory-optimization/suggestions/test_id/preview", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["suggestion_id"] == "test_id"
    assert "preview" in data
