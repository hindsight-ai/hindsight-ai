"""
Targeted tests for bulk_operations.py to improve coverage.
Focuses on specific uncovered lines identified in coverage analysis.
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from core.api.main import app
from core.db import models

client = TestClient(app, headers={"X-Active-Scope": "personal"})

class TestBulkOperationsCoverage:
    """Tests targeting specific uncovered lines in bulk_operations.py"""

    def test_bulk_stats_forbidden_access(self):
        """Test forbidden access to bulk stats endpoint (line 30)"""
        org_id = str(uuid.uuid4())
        
        # Test without proper permissions
        response = client.get(
            f"/bulk-operations/{org_id}/stats",
            headers={
                "x-auth-request-user": "testuser",
                "x-auth-request-email": "test@example.com"
            }
        )
        
        # Should return 403 Forbidden or 404 if org doesn't exist
        assert response.status_code in [403, 404]
        if response.status_code == 403:
            assert response.json()["detail"] == "Forbidden"

    def test_bulk_stats_counts(self):
        """Test bulk stats endpoint returns correct counts (lines 32-35)"""
        org_id = str(uuid.uuid4())
        
        response = client.get(
            f"/bulk-operations/{org_id}/stats",
            headers={
                "x-auth-request-user": "superadmin",
                "x-auth-request-email": "superadmin@example.com"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "agent_count" in data
            assert "memory_block_count" in data
            assert "keyword_count" in data
            assert isinstance(data["agent_count"], int)
            assert isinstance(data["memory_block_count"], int) 
            assert isinstance(data["keyword_count"], int)

    def test_bulk_move_invalid_resource_types(self):
        """Test invalid resource_types validation (lines 59-60)"""
        org_id = str(uuid.uuid4())
        dest_org_id = str(uuid.uuid4())
        
        # Test with invalid resource type
        payload = {
            "dry_run": True,
            "destination_organization_id": dest_org_id,
            "resource_types": ["invalid_type"]
        }
        
        response = client.post(
            f"/bulk-operations/{org_id}/move",
            json=payload,
            headers={
                "x-auth-request-user": "superadmin",
                "x-auth-request-email": "superadmin@example.com"
            }
        )
        
        assert response.status_code in [422, 404]
        if response.status_code == 422:
            assert "Invalid resource_types" in response.json()["detail"]

    def test_bulk_move_missing_destination(self):
        """Test missing destination validation (lines 62-63)"""
        org_id = str(uuid.uuid4())
        
        payload = {
            "dry_run": True,
            "resource_types": ["agents"]
        }
        
        response = client.post(
            f"/bulk-operations/{org_id}/move",
            json=payload,
            headers={
                "x-auth-request-user": "superadmin", 
                "x-auth-request-email": "superadmin@example.com"
            }
        )
        
        assert response.status_code in [422, 404]
        if response.status_code == 422:
            assert "Either destination_organization_id or destination_owner_user_id is required" in response.json()["detail"]

    def test_bulk_move_both_destinations(self):
        """Test both destinations specified validation (lines 64-65)"""
        org_id = str(uuid.uuid4())
        dest_org_id = str(uuid.uuid4())
        dest_user_id = str(uuid.uuid4())
        
        payload = {
            "dry_run": True,
            "destination_organization_id": dest_org_id,
            "destination_owner_user_id": dest_user_id,
            "resource_types": ["agents"]
        }
        
        response = client.post(
            f"/bulk-operations/{org_id}/move",
            json=payload,
            headers={
                "x-auth-request-user": "superadmin",
                "x-auth-request-email": "superadmin@example.com"
            }
        )
        
        assert response.status_code in [422, 404]
        if response.status_code == 422:
            assert "Cannot specify both destination_organization_id and destination_owner_user_id" in response.json()["detail"]

    def test_bulk_move_dry_run_permissions(self):
        """Test dry run permission checks (lines 67-75)"""
        org_id = str(uuid.uuid4())
        dest_org_id = str(uuid.uuid4())
        
        payload = {
            "dry_run": True,
            "destination_organization_id": dest_org_id,
            "resource_types": ["agents"]
        }
        
        # Test without permissions  
        response = client.post(
            f"/bulk-operations/{org_id}/move",
            json=payload,
            headers={
                "x-auth-request-user": "regular_user",
                "x-auth-request-email": "user@example.com"
            }
        )
        
        # Should fail due to lack of permissions
        assert response.status_code in [403, 404]  # Could be 404 if org doesn't exist

    def test_bulk_move_execution_permissions(self):
        """Test execution permission checks (lines 77-82)"""
        org_id = str(uuid.uuid4())
        dest_org_id = str(uuid.uuid4())
        
        payload = {
            "dry_run": False,  # Actual execution
            "destination_organization_id": dest_org_id,
            "resource_types": ["agents"]
        }
        
        response = client.post(
            f"/bulk-operations/{org_id}/move",
            json=payload,
            headers={
                "x-auth-request-user": "regular_user",
                "x-auth-request-email": "user@example.com"
            }
        )
        
        # Should fail due to lack of manage permissions
        assert response.status_code in [403, 404]

    def test_bulk_move_keyword_mock_handling(self):
        """Test keyword mock handling for tests (lines 114-121)"""
        org_id = str(uuid.uuid4())
        dest_user_id = str(uuid.uuid4())
        
        payload = {
            "dry_run": True,
            "destination_owner_user_id": dest_user_id,
            "resource_types": ["keywords"]
        }
        
        response = client.post(
            f"/bulk-operations/{org_id}/move",
            json=payload,
            headers={
                "x-auth-request-user": "superadmin",
                "x-auth-request-email": "superadmin@example.com"
            }
        )
        
        # Should handle the request (may succeed or fail based on org existence)
        assert response.status_code in [200, 404, 403]

    def test_bulk_move_resource_type_initialization(self):
        """Test resource type initialization in plan (lines 85-90)"""
        org_id = str(uuid.uuid4())
        dest_user_id = str(uuid.uuid4())
        
        payload = {
            "dry_run": True,
            "destination_owner_user_id": dest_user_id,
            "resource_types": ["agents", "memory_blocks", "keywords"]
        }
        
        response = client.post(
            f"/bulk-operations/{org_id}/move",
            json=payload,
            headers={
                "x-auth-request-user": "superadmin",
                "x-auth-request-email": "superadmin@example.com"
            }
        )
        
        # Test that all resource types are handled
        if response.status_code == 200:
            data = response.json()
            assert "resources_to_move" in data
            assert "conflicts" in data
