"""
Test to reproduce and prevent regression of archived memory blocks frontend issue.
Tests the missing /memory-blocks/archived endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from core.api.main import app

client = TestClient(app, headers={"X-Active-Scope": "personal"})

class TestArchivedMemoryBlocksFrontendIssue:
    """Tests to reproduce and prevent the archived memory blocks frontend issue"""

    def test_archived_memory_blocks_endpoint_now_works(self):
        """
        GREEN: The endpoint now works correctly after our fix.
        Previously this was returning 422 because 'archived' was being parsed as a UUID.
        """
        # This is the exact request the frontend is making to the archived endpoint
        response = client.get(
            "/memory-blocks/archived/",
            params={
                "search_query": "",  
                "agent_id": "",      
                "conversation_id": "",  
                "feedback_score_range": "0,100",
                "retrieval_count_range": "0,1000",
                "start_date": "",
                "end_date": "",
                "keywords": "",
                "search_type": "fulltext",
                "min_score": "",
                "similarity_threshold": "",
                "fulltext_weight": "",
                "semantic_weight": "",
                "min_combined_score": "",
                "min_feedback_score": "0",
                "max_feedback_score": "100", 
                "min_retrieval_count": "0",
                "max_retrieval_count": "1000",
                "skip": "0",
                "sort_by": "created_at",
                "sort_order": "desc",
                "limit": "10"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        # After our fix, this should now work correctly
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        # Should return 200 and proper response structure
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_items" in data
        assert "total_pages" in data

    def test_archived_memory_blocks_with_regular_endpoint_works(self):
        """
        BLUE: Test that the regular endpoint with include_archived=true works
        This shows the current working approach
        """
        response = client.get(
            "/memory-blocks/",
            params={
                "include_archived": "true",
                "skip": "0",
                "limit": "10"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        print(f"Regular endpoint with include_archived response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_items" in data

    def test_archived_endpoint_with_simple_params_works(self):
        """
        GREEN: Test the archived endpoint with simpler parameters to ensure it works
        """
        response = client.get(
            "/memory-blocks/archived/",
            params={
                "search_query": "",
                "agent_id": "",
                "conversation_id": "",
                "skip": "0", 
                "sort_by": "created_at",
                "sort_order": "desc",
                "limit": "10"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        print(f"Archived endpoint response: {response.status_code}")
        # After our fix, this should work
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_items" in data
        assert "total_pages" in data
