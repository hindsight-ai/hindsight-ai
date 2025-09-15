"""
Test to reproduce and prevent regression of frontend memory blocks loading issue.
Tests the specific 422 error caused by empty string UUID parameters.
"""

import pytest
from fastapi.testclient import TestClient

from core.api.main import app

client = TestClient(app, headers={"X-Active-Scope": "personal"})

class TestMemoryBlocksFrontendIssue:
    """Tests to reproduce and prevent the frontend memory blocks loading issue"""

    def test_memory_blocks_with_empty_string_uuids_should_work(self):
        """
        GREEN: Frontend can send empty string UUIDs and they are handled gracefully.
        Empty strings are converted to None, which means "no filter" - this is correct behavior.
        """
        # This is the exact request the frontend is making
        response = client.get(
            "/memory-blocks/",
            params={
                "search_query": "",  # Empty string - OK
                "agent_id": "",      # Empty string - converted to None (no filter)
                "conversation_id": "",  # Empty string - converted to None (no filter)
                "skip": "0",
                "sort_by": "created_at",
                "sort_order": "desc", 
                "include_archived": "false",
                "limit": "12"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        # This should work correctly (200) - empty strings are handled gracefully
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        assert response.status_code == 200
        # Should return a valid pagination response
        response_data = response.json()
        assert "items" in response_data
        assert "total_items" in response_data
        assert "total_pages" in response_data

    def test_memory_blocks_with_none_uuids_should_work(self):
        """
        This test shows what SHOULD work - when UUIDs are properly None
        """
        response = client.get(
            "/memory-blocks/",
            params={
                "search_query": "",
                # agent_id and conversation_id omitted (None by default)
                "skip": "0", 
                "sort_by": "created_at",
                "sort_order": "desc",
                "include_archived": "false",
                "limit": "12"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        # This should work (200) or fail with auth issues (401/403), not validation (422)
        assert response.status_code in [200, 401, 403]

    def test_memory_blocks_with_valid_uuids_should_work(self):
        """
        Test that valid UUIDs work correctly
        """
        import uuid
        
        response = client.get(
            "/memory-blocks/",
            params={
                "search_query": "",
                "agent_id": str(uuid.uuid4()),
                "conversation_id": str(uuid.uuid4()),
                "skip": "0",
                "sort_by": "created_at", 
                "sort_order": "desc",
                "include_archived": "false",
                "limit": "12"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        # Should work or fail with business logic, not validation
        assert response.status_code in [200, 401, 403, 404]

    def test_memory_blocks_with_invalid_uuid_format_should_fail_422(self):
        """
        Ensure that truly malformed UUIDs (not empty strings) still get validation errors
        """
        response = client.get(
            "/memory-blocks/",
            params={
                "search_query": "",
                "agent_id": "invalid-uuid-format",  # Malformed UUID - should fail
                "conversation_id": "",
                "skip": "0",
                "sort_by": "created_at",
                "sort_order": "desc",
                "include_archived": "false",
                "limit": "12"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        # Should fail with 422 for invalid UUID format
        assert response.status_code == 422
        error_detail = response.json().get("detail", "")
        assert "Invalid UUID format" in str(error_detail)
