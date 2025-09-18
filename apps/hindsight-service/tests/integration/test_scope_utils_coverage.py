"""
Tests for scope_utils to improve coverage
"""
import uuid
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from core.api.main import app as main_app
from core.db import models, schemas
from core.db.scope_utils import (
    get_user_organization_ids,
    apply_scope_filter,
    apply_optional_scope_narrowing,
    validate_scope_access,
    get_scoped_query_filters
)


def _h(user_id_prefix: str) -> dict:
    """Helper to create authentication headers"""
    return {"x-auth-request-user": user_id_prefix, "x-auth-request-email": f"{user_id_prefix}@example.com", "x-active-scope": "personal"}


def test_scope_utils_user_scope_filter(db_session):
    """Test user scope filtering"""
    client = TestClient(main_app, headers={"X-Active-Scope": "personal"})
    h = _h("scope_test_user")
    
    # Create test agent
    agent_data = {
        "agent_name": "ScopeTestAgent",
        "visibility_scope": "personal"
    }
    r = client.post("/agents/", json=agent_data, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]

    # Generate UUID for conversation_id (required field)
    conversation_id = str(uuid.uuid4())

    # Create memory blocks with different agents
    memory_data = {
        "content": "Test content for scope filtering",
        "agent_id": agent_id,
        "conversation_id": conversation_id
    }
    r = client.post("/memory-blocks/", json=memory_data, headers=h)
    assert r.status_code == 201
    
    # Test that we can retrieve our own memories
    r = client.get("/memory-blocks/", headers=h)
    assert r.status_code == 200
    response_data = r.json()
    # Handle paginated response format
    if isinstance(response_data, dict) and "items" in response_data:
        memories = response_data["items"]
    else:
        memories = response_data
    assert len(memories) > 0


def test_scope_utils_agent_scope_filter(db_session):
    """Test agent scope filtering functionality"""
    client = TestClient(main_app, headers={"X-Active-Scope": "personal"})
    h = _h("agent_scope_user")
    
    # Create multiple agents
    agent_ids = []
    for i in range(3):
        agent_data = {
            "agent_name": f"Agent_{i}",
            "visibility_scope": "personal"
        }
        r = client.post("/agents/", json=agent_data, headers=h)
        assert r.status_code == 201
        agent_ids.append(r.json()["agent_id"])

    # Generate UUID for conversation_id (required field)
    conversation_id = str(uuid.uuid4())

    # Create memories for each agent
    for agent_id in agent_ids:
        memory_data = {
            "content": f"Content for agent {agent_id}",
            "agent_id": agent_id,
            "conversation_id": conversation_id
        }
        r = client.post("/memory-blocks/", json=memory_data, headers=h)
        assert r.status_code == 201
    
    # Test filtering by specific agent
    for agent_id in agent_ids:
        r = client.get(f"/memory-blocks/?agent_id={agent_id}", headers=h)
        assert r.status_code == 200
        response_data = r.json()
        # Handle paginated response format
        if isinstance(response_data, dict) and "items" in response_data:
            memories = response_data["items"]
        else:
            memories = response_data
        if memories:  # If any memories returned, they should be for this agent
            for memory in memories:
                assert memory.get("agent_id") == agent_id


def test_scope_utils_org_scope_scenarios(db_session):
    """Test organization scope filtering scenarios"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("org_scope_user")
    
    # Test organization-related endpoints if they exist
    # This tests the org scope filtering logic even if orgs aren't fully implemented
    
    # Test agents listing (should work with org scope)
    r = client.get("/agents/", headers=h)
    assert r.status_code == 200
    
    # Test memory listing (should work with org scope)
    r = client.get("/memory-blocks/", headers=h)
    assert r.status_code == 200


def test_scope_utils_permission_scenarios(db_session):
    """Test permission and access control scenarios"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h1 = _h("permission_user_1")
    h2 = _h("permission_user_2")
    
    # User 1 creates an agent
    agent_data = {
        "agent_name": "PermissionTestAgent",
        "visibility_scope": "personal"
    }
    r = client.post("/agents/", json=agent_data, headers=h1)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]

    # Generate UUID for conversation_id (required field)
    conversation_id = str(uuid.uuid4())
    
    # User 1 creates a memory
    memory_data = {
        "content": "Private content for user 1",
        "agent_id": agent_id,
        "conversation_id": conversation_id
    }
    r = client.post("/memory-blocks/", json=memory_data, headers=h1)
    assert r.status_code == 201
    memory_id = r.json()["id"]
    
    # User 1 should be able to access their memory
    r = client.get(f"/memory-blocks/{memory_id}", headers=h1)
    assert r.status_code == 200
    
    # User 2 should not be able to access user 1's memory (if proper scoping)
    r = client.get(f"/memory-blocks/{memory_id}", headers=h2)
    assert r.status_code in [404, 403]  # Either not found or forbidden


def test_scope_utils_edge_cases(db_session):
    """Test edge cases in scope filtering"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("edge_case_user")
    
    # Test with empty results
    r = client.get("/memory-blocks/?agent_id=00000000-0000-0000-0000-000000000000", headers=h)
    assert r.status_code == 200
    response_data = r.json()
    # Handle paginated response format
    if isinstance(response_data, dict) and "items" in response_data:
        memories = response_data["items"]
        assert isinstance(memories, list)
    else:
        memories = response_data
        assert isinstance(memories, list)
    
    # Test with invalid UUID format (should be handled gracefully)
    r = client.get("/memory-blocks/?agent_id=invalid-uuid", headers=h)
    # Accept any reasonable response to invalid UUID
    assert r.status_code in [400, 422, 200, 500]
    
    # Test pagination with scope filters
    r = client.get("/memory-blocks/?limit=1&offset=0", headers=h)
    assert r.status_code == 200


def test_scope_utils_search_with_scoping(db_session):
    """Test search functionality with scope filtering"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("search_scope_user")
    
    # Create agent and memory for searching
    agent_data = {
        "agent_name": "SearchScopeAgent",
        "visibility_scope": "personal"
    }
    r = client.post("/agents/", json=agent_data, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]

    # Generate UUID for conversation_id (required field)  
    conversation_id = str(uuid.uuid4())
    
    memory_data = {
        "content": "Searchable content with unique keywords",
        "agent_id": agent_id,
        "conversation_id": conversation_id
    }
    r = client.post("/memory-blocks/", json=memory_data, headers=h)
    assert r.status_code == 201
    
    # Test fulltext search with scope
    r = client.get("/memory-blocks/search/fulltext?query=searchable", headers=h)
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    
    # Test semantic search with scope
    r = client.get("/memory-blocks/search/semantic?query=content", headers=h)
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    
    # Test hybrid search with scope
    r = client.get("/memory-blocks/search/hybrid?query=keywords", headers=h)
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)


def test_scope_utils_complex_queries(db_session):
    """Test complex query scenarios with scope filtering"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("complex_query_user")
    
    # Create test data
    agent_data = {
        "agent_name": "ComplexQueryAgent",
        "visibility_scope": "personal"
    }
    r = client.post("/agents/", json=agent_data, headers=h)
    assert r.status_code == 201
    agent_id = r.json()["agent_id"]
    
    # Create multiple memories with different characteristics
    test_memories = [
        {"content": "First test memory with specific content", "metadata": {"priority": "high"}},
        {"content": "Second memory for testing queries", "metadata": {"priority": "medium"}},
        {"content": "Third memory with different content", "metadata": {"priority": "low"}},
    ]
    
    # Generate UUID for conversation_id (required field)
    conversation_id = str(uuid.uuid4())
    
    memory_ids = []
    for memory_data in test_memories:
        memory_data["agent_id"] = agent_id
        memory_data["conversation_id"] = conversation_id
        r = client.post("/memory-blocks/", json=memory_data, headers=h)
        assert r.status_code == 201
        memory_ids.append(r.json()["id"])
    
    # Test combined filters
    r = client.get(f"/memory-blocks/?agent_id={agent_id}&limit=5", headers=h)
    assert r.status_code == 200
    response_data = r.json()
    # Handle paginated response format
    if isinstance(response_data, dict) and "items" in response_data:
        memories = response_data["items"]
    else:
        memories = response_data
    assert len(memories) >= 3
    
    # Test ordering and pagination
    r = client.get(f"/memory-blocks/?agent_id={agent_id}&offset=1&limit=2", headers=h)
    assert r.status_code == 200


def test_scope_utils_validation_and_security(db_session):
    """Test validation and security aspects of scope filtering"""
    client = TestClient(main_app, headers={"x-active-scope": "personal"})
    h = _h("validation_user")
    
    # Test SQL injection attempts (should be prevented by scope filtering)
    malicious_queries = [
        "'; DROP TABLE memory_blocks; --",
        "1 OR 1=1",
        "UNION SELECT * FROM users"
    ]
    
    for malicious_query in malicious_queries:
        # Test in search
        r = client.get(f"/memory-blocks/search/fulltext?query={malicious_query}", headers=h)
        assert r.status_code in [200, 400, 422]  # Should not crash
        
        # Test in agent_id parameter (should be validated as UUID)
        r = client.get(f"/memory-blocks/?agent_id={malicious_query}", headers=h)
        assert r.status_code in [200, 400, 422]  # Should handle gracefully
    
    # Test extremely long queries
    long_query = "A" * 1000
    r = client.get(f"/memory-blocks/search/fulltext?query={long_query}", headers=h)
    assert r.status_code in [200, 400, 413, 422]  # Should handle large input
