"""
Test script for the dynamic role-based permission system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.role_permissions import get_role_permissions, validate_role, get_allowed_roles, update_permissions_for_role

def test_role_permissions():
    """Test the dynamic role permission system."""
    print("Testing dynamic role-based permission system...\n")

    # Test getting permissions for each role
    roles = get_allowed_roles()
    print(f"Allowed roles: {sorted(roles)}\n")

    for role in sorted(roles):
        permissions = get_role_permissions(role)
        print(f"Role '{role}': can_read={permissions['can_read']}, can_write={permissions['can_write']}")

    print("\nTesting permission overrides...")
    # Test permission overrides
    editor_perms = update_permissions_for_role("editor", can_write=False)
    print(f"Editor with write disabled: {editor_perms}")

    viewer_perms = update_permissions_for_role("viewer", can_write=True)
    print(f"Viewer with write enabled: {viewer_perms}")

    print("\nTesting role validation...")
    # Test valid roles
    try:
        validate_role("owner")
        print("✓ 'owner' role validated successfully")
    except ValueError as e:
        print(f"✗ 'owner' validation failed: {e}")

    # Test invalid role
    try:
        validate_role("superuser")
        print("✗ 'superuser' should have failed validation")
    except ValueError as e:
        print(f"✓ 'superuser' correctly rejected: {e}")

    print("\nAll tests completed!")

if __name__ == "__main__":
    test_role_permissions()
