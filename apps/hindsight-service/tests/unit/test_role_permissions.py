import pytest
from core.utils.role_permissions import (
    get_role_permissions,
    validate_role,
    get_allowed_roles,
    update_permissions_for_role,
    ROLE_PERMISSIONS
)


class TestRolePermissions:
    """Unit tests for the dynamic role-based permission system."""

    def test_get_role_permissions_owner(self):
        """Test getting permissions for owner role."""
        permissions = get_role_permissions("owner")
        assert permissions["can_read"] is True
        assert permissions["can_write"] is True

    def test_get_role_permissions_admin(self):
        """Test getting permissions for admin role."""
        permissions = get_role_permissions("admin")
        assert permissions["can_read"] is True
        assert permissions["can_write"] is True

    def test_get_role_permissions_editor(self):
        """Test getting permissions for editor role."""
        permissions = get_role_permissions("editor")
        assert permissions["can_read"] is True
        assert permissions["can_write"] is True

    def test_get_role_permissions_viewer(self):
        """Test getting permissions for viewer role."""
        permissions = get_role_permissions("viewer")
        assert permissions["can_read"] is True
        assert permissions["can_write"] is False

    def test_get_role_permissions_invalid_role(self):
        """Test getting permissions for invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Unknown role: invalid"):
            get_role_permissions("invalid")

    def test_get_role_permissions_returns_copy(self):
        """Test that get_role_permissions returns a copy, not the original dict."""
        permissions1 = get_role_permissions("owner")
        permissions2 = get_role_permissions("owner")

        # Modify one and ensure the other is not affected
        permissions1["can_write"] = False
        assert permissions2["can_write"] is True

    def test_validate_role_valid_roles(self):
        """Test validating all valid roles."""
        for role in ["owner", "admin", "editor", "viewer"]:
            # Should not raise any exception
            validate_role(role)

    def test_validate_role_invalid_role(self):
        """Test validating invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role 'invalid'"):
            validate_role("invalid")

    def test_get_allowed_roles(self):
        """Test getting the set of allowed roles."""
        roles = get_allowed_roles()
        expected_roles = {"owner", "admin", "editor", "viewer"}
        assert roles == expected_roles
        assert isinstance(roles, set)

    def test_get_allowed_roles_returns_copy(self):
        """Test that get_allowed_roles returns a copy, not the original set."""
        roles1 = get_allowed_roles()
        roles2 = get_allowed_roles()

        # Modify one and ensure the other is not affected
        roles1.add("new_role")
        assert "new_role" not in roles2

    def test_update_permissions_for_role_no_overrides(self):
        """Test updating permissions with no overrides."""
        permissions = update_permissions_for_role("viewer")
        assert permissions["can_read"] is True
        assert permissions["can_write"] is False

    def test_update_permissions_for_role_with_can_read_override(self):
        """Test updating permissions with can_read override."""
        permissions = update_permissions_for_role("viewer", can_read=False)
        assert permissions["can_read"] is False
        assert permissions["can_write"] is False

    def test_update_permissions_for_role_with_can_write_override(self):
        """Test updating permissions with can_write override."""
        permissions = update_permissions_for_role("viewer", can_write=True)
        assert permissions["can_read"] is True
        assert permissions["can_write"] is True

    def test_update_permissions_for_role_with_both_overrides(self):
        """Test updating permissions with both overrides."""
        permissions = update_permissions_for_role("owner", can_read=False, can_write=False)
        assert permissions["can_read"] is False
        assert permissions["can_write"] is False

    def test_update_permissions_for_role_invalid_role(self):
        """Test updating permissions for invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Unknown role: invalid"):
            update_permissions_for_role("invalid")

    def test_role_permissions_configuration_structure(self):
        """Test that ROLE_PERMISSIONS has the expected structure."""
        assert isinstance(ROLE_PERMISSIONS, dict)
        assert len(ROLE_PERMISSIONS) == 4  # owner, admin, editor, viewer

        for role, permissions in ROLE_PERMISSIONS.items():
            assert isinstance(permissions, dict)
            assert "can_read" in permissions
            assert "can_write" in permissions
            assert isinstance(permissions["can_read"], bool)
            assert isinstance(permissions["can_write"], bool)

    def test_role_permissions_logical_consistency(self):
        """Test that role permissions follow logical hierarchy."""
        # Higher roles should have at least the same permissions as lower roles
        viewer_perms = ROLE_PERMISSIONS["viewer"]
        editor_perms = ROLE_PERMISSIONS["editor"]
        admin_perms = ROLE_PERMISSIONS["admin"]
        owner_perms = ROLE_PERMISSIONS["owner"]

        # All roles should be able to read
        assert viewer_perms["can_read"] is True
        assert editor_perms["can_read"] is True
        assert admin_perms["can_read"] is True
        assert owner_perms["can_read"] is True

        # Only viewer should not be able to write
        assert viewer_perms["can_write"] is False
        assert editor_perms["can_write"] is True
        assert admin_perms["can_write"] is True
        assert owner_perms["can_write"] is True

    def test_role_permissions_immutability(self):
        """Test that modifying returned permissions doesn't affect the original configuration."""
        original_viewer_write = ROLE_PERMISSIONS["viewer"]["can_write"]

        # Get permissions and modify them
        permissions = get_role_permissions("viewer")
        permissions["can_write"] = True

        # Original configuration should be unchanged
        assert ROLE_PERMISSIONS["viewer"]["can_write"] == original_viewer_write
