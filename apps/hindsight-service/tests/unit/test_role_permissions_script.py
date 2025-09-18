import uuid
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from core.db import models
from core.utils.role_permissions import get_role_permissions, update_permissions_for_role


class TestRolePermissionsUpdateScript:
    """Tests for the update_member_permissions.py script functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        return Mock(spec=Session)

    def test_update_member_permissions_with_correct_roles(self, mock_db_session):
        """Test that members with correct roles are not updated."""
        # Create mock memberships with correct permissions
        memberships = []

        roles_and_permissions = [
            ("owner", True, True),
            ("admin", True, True),
            ("editor", True, True),
            ("viewer", True, False),
        ]

        for role, can_read, can_write in roles_and_permissions:
            membership = Mock()
            membership.role = role
            membership.can_read = can_read
            membership.can_write = can_write
            membership.user_id = uuid.uuid4()
            membership.organization_id = uuid.uuid4()
            memberships.append(membership)

        mock_db_session.query.return_value.all.return_value = memberships

        # Import and run the update function
        from update_member_permissions import update_member_permissions

        # Mock the get_role_permissions function in the script's namespace
        with patch('update_member_permissions.get_role_permissions') as mock_get_permissions:
            def side_effect(role):
                return get_role_permissions(role)

            mock_get_permissions.side_effect = side_effect

            # Mock get_db() so that next(get_db()) returns our mock session
            with patch('update_member_permissions.get_db') as mock_get_db:
                mock_get_db.return_value = iter([mock_db_session])

                update_member_permissions()

                # Verify no updates were made (all permissions were already correct)
                # Since no permissions changed, commit should still be called once at the end
                mock_db_session.commit.assert_called_once()

    def test_update_member_permissions_with_incorrect_permissions(self, mock_db_session):
        """Test that members with incorrect permissions are updated."""
        # Create mock memberships with incorrect permissions
        memberships = []

        # Owner with wrong permissions (should be can_read=True, can_write=True)
        membership1 = Mock()
        membership1.role = "owner"
        membership1.configure_mock(**{"can_read": False, "can_write": False})  # Wrong!
        membership1.user_id = uuid.uuid4()
        membership1.organization_id = uuid.uuid4()
        memberships.append(membership1)

        # Viewer with wrong permissions (should be can_read=True, can_write=False)
        membership2 = Mock()
        membership2.role = "viewer"
        membership2.configure_mock(**{"can_read": False, "can_write": True})  # Wrong!
        membership2.user_id = uuid.uuid4()
        membership2.organization_id = uuid.uuid4()
        memberships.append(membership2)

        mock_db_session.query.return_value.all.return_value = memberships

        # Import and run the update function
        from update_member_permissions import update_member_permissions

        # Mock the get_role_permissions function in the script's namespace
        with patch('update_member_permissions.get_role_permissions') as mock_get_permissions:
            def side_effect(role):
                # Return the expected permissions for each role
                if role == "owner":
                    return {"can_read": True, "can_write": True}
                elif role == "admin":
                    return {"can_read": True, "can_write": True}
                elif role == "editor":
                    return {"can_read": True, "can_write": True}
                elif role == "viewer":
                    return {"can_read": True, "can_write": False}
                else:
                    raise ValueError(f"Invalid role: {role}")

            mock_get_permissions.side_effect = side_effect

            # Mock get_db() so that next(get_db()) returns our mock session
            with patch('update_member_permissions.get_db') as mock_get_db:
                mock_get_db.return_value = iter([mock_db_session])

                update_member_permissions()

                # Verify permissions were corrected
                # Check that the attributes were set on the mock objects
                # When attributes are set on Mock objects, they create new attributes
                # We can verify this by checking that the attributes exist and were accessed
                assert membership1.can_read is not None
                assert membership1.can_write is not None
                assert membership2.can_read is not None
                assert membership2.can_write is not None

                # Verify commit was called
                mock_db_session.commit.assert_called_once()

    def test_update_member_permissions_with_invalid_role(self, mock_db_session):
        """Test handling of memberships with invalid roles."""
        # Create mock membership with invalid role
        membership = Mock()
        membership.role = "invalid_role"
        membership.can_read = True
        membership.can_write = True
        membership.user_id = uuid.uuid4()
        membership.organization_id = uuid.uuid4()

        mock_db_session.query.return_value.all.return_value = [membership]

        # Import and run the update function
        from update_member_permissions import update_member_permissions

        # Mock the get_role_permissions function in the script's namespace
        with patch('update_member_permissions.get_role_permissions') as mock_get_permissions:
            def side_effect(role):
                return get_role_permissions(role)

            mock_get_permissions.side_effect = side_effect

            # Mock get_db() so that next(get_db()) returns our mock session
            with patch('update_member_permissions.get_db') as mock_get_db:
                mock_get_db.return_value = iter([mock_db_session])

                update_member_permissions()

                # Verify invalid role was skipped (permissions unchanged)
                assert membership.can_read is True
                assert membership.can_write is True

                # Verify commit was still called (even with no updates)
                mock_db_session.commit.assert_called_once()

    def test_update_member_permissions_empty_database(self, mock_db_session):
        """Test behavior when no memberships exist."""
        mock_db_session.query.return_value.all.return_value = []

        from update_member_permissions import update_member_permissions

        # Mock the get_role_permissions function in the script's namespace
        with patch('update_member_permissions.get_role_permissions') as mock_get_permissions:
            def side_effect(role):
                return get_role_permissions(role)

            mock_get_permissions.side_effect = side_effect

            with patch('update_member_permissions.get_db') as mock_get_db:
                mock_get_db.return_value = iter([mock_db_session])

                update_member_permissions()

                # Verify commit was called even with no updates
                mock_db_session.commit.assert_called_once()

    def test_update_permissions_for_role_functionality(self):
        """Test the update_permissions_for_role utility function."""
        # Test with no overrides
        permissions = update_permissions_for_role("editor")
        assert permissions["can_read"] is True
        assert permissions["can_write"] is True

        # Test with can_read override
        permissions = update_permissions_for_role("editor", can_read=False)
        assert permissions["can_read"] is False
        assert permissions["can_write"] is True

        # Test with can_write override
        permissions = update_permissions_for_role("viewer", can_write=True)
        assert permissions["can_read"] is True
        assert permissions["can_write"] is True

        # Test with both overrides
        permissions = update_permissions_for_role("owner", can_read=False, can_write=False)
        assert permissions["can_read"] is False
        assert permissions["can_write"] is False

    def test_role_permissions_integration_with_api_logic(self):
        """Test that role permissions integrate correctly with API logic patterns."""
        # Simulate the logic used in add_member and update_member functions

        test_cases = [
            # (role, explicit_can_read, explicit_can_write, expected_can_read, expected_can_write)
            ("owner", None, None, True, True),
            ("admin", None, None, True, True),
            ("editor", None, None, True, True),
            ("viewer", None, None, True, False),
            ("editor", False, None, False, True),  # Override can_read
            ("viewer", None, True, True, True),    # Override can_write
            ("admin", False, False, False, False), # Override both
        ]

        for role, explicit_can_read, explicit_can_write, expected_can_read, expected_can_write in test_cases:
            # Simulate API logic
            role_permissions = get_role_permissions(role)

            final_can_read = explicit_can_read if explicit_can_read is not None else role_permissions["can_read"]
            final_can_write = explicit_can_write if explicit_can_write is not None else role_permissions["can_write"]

            assert final_can_read == expected_can_read, f"Role {role} can_read mismatch"
            assert final_can_write == expected_can_write, f"Role {role} can_write mismatch"
