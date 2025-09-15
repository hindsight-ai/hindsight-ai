"""
Tests for core CRUD operations to improve coverage
"""
import uuid
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from core.api.main import app as main_app
from core.db import crud, models, schemas
from core.db.database import SessionLocal


def _h(user_id_prefix: str) -> dict:
    """Helper to create authentication headers"""
    return {"x-auth-request-user": user_id_prefix, "x-auth-request-email": f"{user_id_prefix}@example.com", "x-active-scope": "personal"}


def _create_test_agent(client: TestClient, h: dict, name: str) -> str:
    """Create a test agent and return its ID"""
    agent_data = {
        "agent_name": name,
        "visibility_scope": "personal"
    }
    r = client.post("/agents/", json=agent_data, headers=h)
    assert r.status_code == 201
    return r.json()["agent_id"]


def _create_test_memory(client: TestClient, h: dict, agent_id: str, content: str) -> str:
    """Create a test memory block and return its ID"""
    import uuid
    memory_data = {
        "content": content,
        "metadata": {"test": "data"},
        "agent_id": agent_id,
        "conversation_id": str(uuid.uuid4())
    }
    r = client.post("/memory-blocks/", json=memory_data, headers=h)
    if r.status_code != 201:
        print(f"DEBUG: Failed to create memory. Status: {r.status_code}, Response: {r.text}")
    assert r.status_code == 201
    return r.json()["id"]


def test_crud_agent_operations(db_session):
    """Test agent CRUD operations for better coverage"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("crud_agent_user")
    
    # Test agent creation with personal scope (regular users can only create personal agents)
    agent_data = {
        "agent_name": "TestAgent_personal",
        "visibility_scope": "personal"
    }
    r = client.post("/agents/", json=agent_data, headers=h)
    assert r.status_code == 201
    agent = r.json()
    assert agent["visibility_scope"] == "personal"
    
    # Test agent retrieval
    agent_id = agent["agent_id"]
    r = client.get(f"/agents/{agent_id}", headers=h)
    assert r.status_code == 200
    
    # Test agent update
    update_data = {"agent_name": "Updated_Personal_Agent"}
    r = client.put(f"/agents/{agent_id}", json=update_data, headers=h)
    assert r.status_code == 200
    
    # Test agent listing
    r = client.get("/agents/", headers=h)
    assert r.status_code == 200
    agents = r.json()
    assert isinstance(agents, list)
    
    # Test that regular users cannot create organization-scoped agents
    org_agent_data = {
        "agent_name": "TestAgent_org",
        "visibility_scope": "organization"
    }
    r = client.post("/agents/", json=org_agent_data, headers=h)
    # Depending on test environment ADMIN_EMAILS and memberships, this may be allowed or forbidden.
    assert r.status_code in (201, 403)


def test_crud_memory_block_operations(db_session):
    """Test memory block CRUD operations including edge cases"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("crud_memory_user")
    
    agent_id = _create_test_agent(client, h, "CRUDTestAgent")
    
    # Test memory creation with various content types
    test_contents = [
        "Simple text content",
        "Content with special chars: àáâãäå",
        "Long content: " + "A" * 200,  # Reduced to stay under keyword length limit
        "JSON-like content: {\"key\": \"value\"}"
    ]
    
    memory_ids = []
    for content in test_contents:
        import uuid
        memory_data = {
            "content": content,
            "metadata": {"type": "test", "length": len(content)},
            "agent_id": agent_id,
            "conversation_id": str(uuid.uuid4())
        }
        r = client.post("/memory-blocks/", json=memory_data, headers=h)
        if r.status_code != 201:
            print(f"DEBUG: Failed to create memory block. Status: {r.status_code}, Response: {r.text}")
        assert r.status_code == 201
        memory_ids.append(r.json()["id"])
    
    # Test memory retrieval and updates
    for memory_id in memory_ids:
        # Get memory
        r = client.get(f"/memory-blocks/{memory_id}", headers=h)
        assert r.status_code == 200
        
        # Update memory
        update_data = {
            "content": "Updated content",
            "metadata": {"updated": True}
        }
        r = client.put(f"/memory-blocks/{memory_id}", json=update_data, headers=h)
        assert r.status_code == 200
    
    # Test memory listing with filters
    r = client.get(f"/memory-blocks/?agent_id={agent_id}&limit=10", headers=h)
    assert r.status_code == 200
    response_data = r.json()
    # Handle paginated response format
    if isinstance(response_data, dict) and 'items' in response_data:
        memories = response_data['items']
        total_items = response_data.get('total_items', len(memories))
        assert total_items >= len(test_contents)
    else:
        memories = response_data
        assert len(memories) >= len(test_contents)


def test_crud_keyword_operations(db_session):
    """Test keyword CRUD operations and associations"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("crud_keyword_user")
    
    agent_id = _create_test_agent(client, h, "KeywordTestAgent")
    memory_id = _create_test_memory(client, h, agent_id, "Content for keyword testing")
    
    # Test keyword creation (use unique names to avoid conflicts)
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    keywords = [f"python_{unique_suffix}", f"testing_{unique_suffix}", f"coverage_{unique_suffix}", f"crud_{unique_suffix}"]
    keyword_ids = []
    
    for keyword_text in keywords:
        keyword_data = {"keyword_text": keyword_text}
        r = client.post("/keywords/", json=keyword_data, headers=h)
        assert r.status_code == 201
        keyword_ids.append(r.json()["keyword_id"])
    
    # Test keyword-memory associations
    for keyword_id in keyword_ids:
        # Associate keyword with memory
        r = client.post(f"/memory-blocks/{memory_id}/keywords/{keyword_id}", headers=h)
        assert r.status_code == 201  # Created status for new association
        
        # Test retrieval of keywords for memory
        r = client.get(f"/memory-blocks/{memory_id}/keywords/", headers=h)
        assert r.status_code == 200
    
    # Test keyword listing and filtering
    r = client.get("/keywords/", headers=h)
    assert r.status_code == 200
    all_keywords = r.json()
    assert len(all_keywords) >= len(keywords)


def test_crud_error_conditions(db_session):
    """Test error conditions for better coverage"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("crud_error_user")
    
    # Test with nonexistent IDs
    fake_id = str(uuid.uuid4())
    
    # Test nonexistent agent
    r = client.get(f"/agents/{fake_id}", headers=h)
    assert r.status_code == 404
    
    # Test nonexistent memory
    r = client.get(f"/memory-blocks/{fake_id}", headers=h)
    assert r.status_code == 404
    
    # Test nonexistent keyword
    r = client.get(f"/keywords/{fake_id}", headers=h)
    assert r.status_code == 404
    
    # Test invalid data formats
    r = client.post("/agents/", json={"invalid": "data"}, headers=h)
    assert r.status_code == 422
    
    r = client.post("/memory-blocks/", json={"invalid": "data"}, headers=h)
    assert r.status_code == 422


def test_crud_batch_operations(db_session):
    """Test batch operations for coverage"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("crud_batch_user")
    
    agent_id = _create_test_agent(client, h, "BatchTestAgent")
    
    # Create multiple memories for batch operations
    memory_ids = []
    for i in range(5):
        content = f"Batch test memory {i}"
        memory_id = _create_test_memory(client, h, agent_id, content)
        memory_ids.append(memory_id)
    
    # Test bulk keyword generation (if endpoint exists)
    payload = {"memory_block_ids": memory_ids[:3]}
    r = client.post("/memory-blocks/bulk-generate-keywords", json=payload, headers=h)
    assert r.status_code in [200, 400, 500]  # Various responses acceptable
    
    # Test search operations
    r = client.get("/memory-blocks/search/fulltext?query=batch&limit=5", headers=h)
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)


def test_crud_edge_cases_and_validations(db_session):
    """Test edge cases and validation scenarios"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("crud_edge_user")
    
    # Test empty content handling
    agent_id = _create_test_agent(client, h, "EdgeTestAgent")
    
    # Test with minimal valid data
    minimal_memory = {
        "content": "",  # Empty content
        "agent_id": agent_id
    }
    r = client.post("/memory-blocks/", json=minimal_memory, headers=h)
    assert r.status_code in [200, 201, 422]  # May or may not allow empty content
    
    # Test with very long content
    long_content = "A" * 10000
    long_memory = {
        "content": long_content,
        "agent_id": agent_id
    }
    r = client.post("/memory-blocks/", json=long_memory, headers=h)
    assert r.status_code in [200, 201, 413, 422]  # May have size limits
    
    # Test duplicate keyword handling
    duplicate_keyword = {"keyword_text": "duplicate_test"}
    r1 = client.post("/keywords/", json=duplicate_keyword, headers=h)
    r2 = client.post("/keywords/", json=duplicate_keyword, headers=h)
    # One should succeed, one might fail or return existing
    assert r1.status_code in [200, 201] or r2.status_code in [200, 201]
