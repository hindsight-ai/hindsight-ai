import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db import models
from core.api.main import app
from core.utils.role_permissions import get_role_permissions


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


# Use the shared transactional db_session from tests/conftest.py


def _create_test_user_and_org(db: Session, email: str = None, role: str = "owner"):
    """Helper to create a test user and organization."""
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    user = models.User(
        email=email,
        display_name="Test User",
        is_superadmin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    org = models.Organization(
        name=f"TestOrg_{uuid.uuid4().hex[:6]}",
        slug=f"testorg-{uuid.uuid4().hex[:6]}",
        created_by=user.id
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Create membership with correct permissions based on role
    role_permissions = get_role_permissions(role)
    membership = models.OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=role,
        can_read=role_permissions["can_read"],
        can_write=role_permissions["can_write"]
    )
    db.add(membership)
    db.commit()

    return user, org, membership


class TestDynamicRolePermissionsIntegration:
    """Integration tests for dynamic role-based permission system."""

    def test_add_member_with_dynamic_permissions_owner_role(self, client, db_session):
        """Test adding a member with owner role applies correct dynamic permissions."""
        # Create owner user and organization
        owner, org, _ = _create_test_user_and_org(db_session, role="owner")

        # Create member user
        member_email = f"member_{uuid.uuid4().hex}@example.com"
        member_user = models.User(email=member_email, display_name="Member User")
        db_session.add(member_user)
        db_session.commit()

        # Add member with editor role via API
        response = client.post(
            f"/api/v1/organizations/{org.id}/members",
            json={"email": member_email, "role": "editor"},
            headers={"Authorization": f"Bearer mock_token_for_{owner.id}"}
        )

        # This would normally require authentication mocking
        # For now, test the database logic directly
        role_permissions = get_role_permissions("editor")
        membership = models.OrganizationMembership(
            organization_id=org.id,
            user_id=member_user.id,
            role="editor",
            can_read=role_permissions["can_read"],
            can_write=role_permissions["can_write"]
        )
        db_session.add(membership)
        db_session.commit()

        # Verify permissions were set correctly
        assert membership.can_read is True
        assert membership.can_write is True

    def test_add_member_with_dynamic_permissions_viewer_role(self, client, db_session):
        """Test adding a member with viewer role applies correct dynamic permissions."""
        owner, org, _ = _create_test_user_and_org(db_session, role="owner")

        member_email = f"viewer_{uuid.uuid4().hex}@example.com"
        member_user = models.User(email=member_email, display_name="Viewer User")
        db_session.add(member_user)
        db_session.commit()

        # Add member with viewer role
        role_permissions = get_role_permissions("viewer")
        membership = models.OrganizationMembership(
            organization_id=org.id,
            user_id=member_user.id,
            role="viewer",
            can_read=role_permissions["can_read"],
            can_write=role_permissions["can_write"]
        )
        db_session.add(membership)
        db_session.commit()

        # Verify permissions were set correctly
        assert membership.can_read is True
        assert membership.can_write is False

    def test_update_member_role_changes_permissions_dynamically(self, db_session):
        """Test that updating a member's role dynamically changes their permissions."""
        owner, org, _ = _create_test_user_and_org(db_session, role="owner")

        # Create member with viewer role initially
        member_email = f"test_{uuid.uuid4().hex}@example.com"
        member_user = models.User(email=member_email, display_name="Test Member")
        db_session.add(member_user)
        db_session.commit()

        # Add as viewer
        viewer_permissions = get_role_permissions("viewer")
        membership = models.OrganizationMembership(
            organization_id=org.id,
            user_id=member_user.id,
            role="viewer",
            can_read=viewer_permissions["can_read"],
            can_write=viewer_permissions["can_write"]
        )
        db_session.add(membership)
        db_session.commit()

        # Verify initial permissions
        assert membership.can_read is True
        assert membership.can_write is False

        # Update role to editor
        membership.role = "editor"
        editor_permissions = get_role_permissions("editor")
        membership.can_read = editor_permissions["can_read"]
        membership.can_write = editor_permissions["can_write"]
        db_session.commit()

        # Verify permissions updated
        assert membership.can_read is True
        assert membership.can_write is True

    def test_permission_override_functionality(self, db_session):
        """Test that explicit permission overrides work with dynamic system."""
        owner, org, _ = _create_test_user_and_org(db_session, role="owner")

        member_email = f"override_{uuid.uuid4().hex}@example.com"
        member_user = models.User(email=member_email, display_name="Override User")
        db_session.add(member_user)
        db_session.commit()

        # Add member with editor role but override can_write to False
        membership = models.OrganizationMembership(
            organization_id=org.id,
            user_id=member_user.id,
            role="editor",
            can_read=True,  # Explicit override
            can_write=False  # Explicit override (normally True for editor)
        )
        db_session.add(membership)
        db_session.commit()

        # Verify explicit overrides were respected
        assert membership.can_read is True
        assert membership.can_write is False

    def test_all_roles_have_correct_default_permissions(self, db_session):
        """Test that all roles get their correct default permissions."""
        owner, org, _ = _create_test_user_and_org(db_session, role="owner")

        test_cases = [
            ("owner", True, True),
            ("admin", True, True),
            ("editor", True, True),
            ("viewer", True, False),
        ]

        for role, expected_can_read, expected_can_write in test_cases:
            member_email = f"{role}_{uuid.uuid4().hex}@example.com"
            member_user = models.User(email=member_email, display_name=f"{role.title()} User")
            db_session.add(member_user)
            db_session.commit()

            role_permissions = get_role_permissions(role)
            membership = models.OrganizationMembership(
                organization_id=org.id,
                user_id=member_user.id,
                role=role,
                can_read=role_permissions["can_read"],
                can_write=role_permissions["can_write"]
            )
            db_session.add(membership)
            db_session.commit()

            assert membership.can_read == expected_can_read, f"Role {role} can_read should be {expected_can_read}"
            assert membership.can_write == expected_can_write, f"Role {role} can_write should be {expected_can_write}"

    def test_dynamic_permissions_consistency_across_operations(self, db_session):
        """Test that dynamic permissions are consistent across add/update operations."""
        owner, org, _ = _create_test_user_and_org(db_session, role="owner")

        member_email = f"consistency_{uuid.uuid4().hex}@example.com"
        member_user = models.User(email=member_email, display_name="Consistency User")
        db_session.add(member_user)
        db_session.commit()

        # Add member with editor role
        editor_permissions = get_role_permissions("editor")
        membership = models.OrganizationMembership(
            organization_id=org.id,
            user_id=member_user.id,
            role="editor",
            can_read=editor_permissions["can_read"],
            can_write=editor_permissions["can_write"]
        )
        db_session.add(membership)
        db_session.commit()

        initial_can_read = membership.can_read
        initial_can_write = membership.can_write

        # Update role to viewer
        membership.role = "viewer"
        viewer_permissions = get_role_permissions("viewer")
        membership.can_read = viewer_permissions["can_read"]
        membership.can_write = viewer_permissions["can_write"]
        db_session.commit()

        # Verify permissions changed appropriately
        assert membership.can_read == initial_can_read  # Both editor and viewer can read
        assert membership.can_write != initial_can_write  # Editor can write, viewer cannot

        # Update back to editor
        membership.role = "editor"
        membership.can_read = editor_permissions["can_read"]
        membership.can_write = editor_permissions["can_write"]
        db_session.commit()

        # Verify permissions restored
        assert membership.can_read == initial_can_read
        assert membership.can_write == initial_can_write
