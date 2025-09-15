"""
Test to debug the archived memory blocks visibility issue.
"""

import pytest
from fastapi.testclient import TestClient

from core.api.main import app

client = TestClient(app, headers={"X-Active-Scope": "personal"})

class TestArchivedVisibilityDebug:
    """Debug tests for archived memory blocks visibility"""

    def test_archived_endpoint_without_auth_shows_only_public(self):
        """
        Test archived endpoint without authentication - should only show public archived blocks
        """
        response = client.get(
            "/memory-blocks/archived",
            params={
                "skip": "0",
                "limit": "10"
            }
            # No authentication headers
        )
        
        print(f"No auth - Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"No auth - Found {data['total_items']} archived blocks")
            print(f"No auth - Items: {[item.get('id') for item in data['items']]}")
        else:
            print(f"No auth - Error: {response.json()}")

    def test_archived_endpoint_with_regular_user_auth(self):
        """
        Test archived endpoint with regular user authentication
        """
        response = client.get(
            "/memory-blocks/archived",
            params={
                "skip": "0",
                "limit": "10"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        print(f"Regular user - Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Regular user - Found {data['total_items']} archived blocks")
            print(f"Regular user - Items: {[item.get('id') for item in data['items']]}")
        else:
            print(f"Regular user - Error: {response.json()}")

    def test_regular_memory_blocks_endpoint_for_comparison(self):
        """
        Test regular memory blocks endpoint to see if we get any data
        """
        response = client.get(
            "/memory-blocks/",
            params={
                "skip": "0",
                "limit": "10"
            },
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        print(f"Regular endpoint - Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Regular endpoint - Found {data['total_items']} non-archived blocks")
            print(f"Regular endpoint - Items: {[item.get('id') for item in data['items']]}")
        else:
            print(f"Regular endpoint - Error: {response.json()}")

    def test_regular_endpoint_with_include_archived_true(self):
        """
        Test regular endpoint with include_archived=true to see all blocks
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
        
        print(f"Include archived - Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Include archived - Found {data['total_items']} total blocks (archived + non-archived)")
            print(f"Include archived - Items: {[item.get('id') for item in data['items']]}")
        else:
            print(f"Include archived - Error: {response.json()}")
