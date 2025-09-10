import uuid
import pytest
from core.api.permissions import can_manage_org, can_read, can_write, can_move_scope
from core.db import models

@pytest.fixture
def user_and_orgs():
    user_id = uuid.uuid4()
    org1 = uuid.uuid4()
    org2 = uuid.uuid4()
    base_ctx = {
        "id": user_id,
        "is_superadmin": False,
        "memberships_by_org": {
            str(org1): {"role": "owner", "can_read": True, "can_write": True},
            str(org2): {"role": "editor", "can_read": True, "can_write": True},
        },
    }
    return user_id, org1, org2, base_ctx


def test_can_manage_org_owner(user_and_orgs):
    _, org1, _, ctx = user_and_orgs
    assert can_manage_org(org1, ctx) is True


def test_can_manage_org_editor_false(user_and_orgs):
    _, _, org2, ctx = user_and_orgs
    assert can_manage_org(org2, ctx) is False


def test_can_manage_org_superadmin(user_and_orgs):
    _, org1, _, ctx = user_and_orgs
    ctx["is_superadmin"] = True
    assert can_manage_org(org1, ctx) is True


def test_can_read_personal_resource(user_and_orgs):
    user_id, _, _, ctx = user_and_orgs
    class R: visibility_scope="personal"; owner_user_id=user_id
    assert can_read(R(), ctx) is True


def test_can_read_personal_other_user(user_and_orgs):
    _, _, _, ctx = user_and_orgs
    class R: visibility_scope="personal"; owner_user_id=uuid.uuid4()
    assert can_read(R(), ctx) is False


def test_can_write_org_editor(user_and_orgs):
    _, _, org2, ctx = user_and_orgs
    class R: visibility_scope="organization"; organization_id=org2
    assert can_write(R(), ctx) is True


def test_can_write_org_viewer_denied(user_and_orgs):
    _, org1, _, ctx = user_and_orgs
    # downgrade role and remove explicit can_write to ensure denial
    ctx["memberships_by_org"][str(org1)]["role"] = "viewer"
    ctx["memberships_by_org"][str(org1)]["can_write"] = False
    class R: visibility_scope="organization"; organization_id=org1
    assert can_write(R(), ctx) is False


def test_can_move_scope_to_org_requires_manage(user_and_orgs):
    _, org1, org2, ctx = user_and_orgs
    class R: visibility_scope="organization"; organization_id=org2; owner_user_id=ctx["id"]
    # org1 owner so allowed
    assert can_move_scope(R(), "organization", org1, ctx) is True
    # downgrade to editor -> still not manage
    ctx["memberships_by_org"][str(org1)]["role"] = "editor"
    assert can_move_scope(R(), "organization", org1, ctx) is False


def test_can_move_scope_personal_owner(user_and_orgs):
    user_id, _, org2, ctx = user_and_orgs
    class R: visibility_scope="organization"; organization_id=org2; owner_user_id=user_id
    assert can_move_scope(R(), "personal", None, ctx) is True


def test_can_move_scope_personal_other(user_and_orgs):
    _, _, org2, ctx = user_and_orgs
    class R: visibility_scope="organization"; organization_id=org2; owner_user_id=uuid.uuid4()
    assert can_move_scope(R(), "personal", None, ctx) is False


def test_superadmin_overrides(user_and_orgs):
    _, org1, _, ctx = user_and_orgs
    ctx["is_superadmin"] = True
    class R: visibility_scope="organization"; organization_id=org1; owner_user_id=uuid.uuid4()
    assert can_write(R(), ctx) is True
    assert can_move_scope(R(), "organization", org1, ctx) is True


# Additional comprehensive tests to improve coverage

from core.api.permissions import (
    get_org_membership, 
    _role_allows_write, 
    _role_allows_manage,
    is_member_of_org,
    can_manage_org_effective
)
from unittest.mock import Mock


def test_get_org_membership_none_cases():
    """Test get_org_membership edge cases."""
    # No user
    assert get_org_membership(str(uuid.uuid4()), None) is None
    
    # No org_id
    assert get_org_membership(None, {"memberships_by_org": {}}) is None
    
    # User with no memberships
    user = {"memberships_by_org": {}, "memberships": []}
    assert get_org_membership(str(uuid.uuid4()), user) is None


def test_get_org_membership_from_list():
    """Test getting membership from memberships list."""
    org_id = str(uuid.uuid4())
    user = {
        "memberships_by_org": {},
        "memberships": [
            {"organization_id": org_id, "role": "admin", "can_read": True, "can_write": True}
        ]
    }
    
    membership = get_org_membership(org_id, user)
    assert membership is not None
    assert membership["role"] == "admin"


def test_get_org_membership_malformed_data():
    """Test get_org_membership with malformed data."""
    user = {
        "memberships_by_org": None,
        "memberships": None
    }
    
    assert get_org_membership(str(uuid.uuid4()), user) is None


def test_role_allows_write():
    """Test _role_allows_write function."""
    assert _role_allows_write("owner") is True
    assert _role_allows_write("admin") is True  
    assert _role_allows_write("editor") is True
    assert _role_allows_write("viewer") is False
    assert _role_allows_write("guest") is False
    assert _role_allows_write("unknown") is False


def test_role_allows_manage():
    """Test _role_allows_manage function."""
    assert _role_allows_manage("owner") is True
    assert _role_allows_manage("admin") is True
    assert _role_allows_manage("editor") is False
    assert _role_allows_manage("viewer") is False


def test_can_read_no_user():
    """Test can_read with no user."""
    class R: visibility_scope="organization"; organization_id=uuid.uuid4()
    assert can_read(R(), None) is False


def test_can_read_public_resource():
    """Test can_read with public resource."""
    class R: visibility_scope="public"; organization_id=uuid.uuid4()
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    assert can_read(R(), user) is True


def test_can_read_organization_non_member():
    """Test can_read organization resource as non-member."""
    org_id = uuid.uuid4()
    class R: visibility_scope="organization"; organization_id=org_id
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    assert can_read(R(), user) is False


def test_can_write_no_user():
    """Test can_write with no user."""
    class R: visibility_scope="organization"; organization_id=uuid.uuid4()
    assert can_write(R(), None) is False


def test_can_write_organization_viewer():
    """Test can_write organization resource as viewer."""
    org_id = str(uuid.uuid4())
    user = {
        "id": str(uuid.uuid4()), 
        "is_superadmin": False, 
        "memberships_by_org": {
            org_id: {"role": "viewer", "can_read": True, "can_write": False}
        }
    }
    class R: visibility_scope="organization"; organization_id=uuid.UUID(org_id)
    assert can_write(R(), user) is False


def test_can_manage_org_no_user():
    """Test can_manage_org with no user."""
    assert can_manage_org(uuid.uuid4(), None) is False


def test_can_manage_org_non_member():
    """Test can_manage_org as non-member."""
    org_id = uuid.uuid4()
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    assert can_manage_org(org_id, user) is False


def test_is_member_of_org_superadmin():
    """Test is_member_of_org for superadmin."""
    user = {"id": str(uuid.uuid4()), "is_superadmin": True, "memberships_by_org": {}}
    assert is_member_of_org(uuid.uuid4(), user) is True


def test_is_member_of_org_no_user():
    """Test is_member_of_org with no user."""
    assert is_member_of_org(uuid.uuid4(), None) is False


def test_is_member_of_org_member():
    """Test is_member_of_org for actual member."""
    org_id = str(uuid.uuid4())
    user = {
        "id": str(uuid.uuid4()),
        "is_superadmin": False,
        "memberships_by_org": {
            org_id: {"role": "member", "can_read": True, "can_write": False}
        }
    }
    assert is_member_of_org(org_id, user) is True


def test_is_member_of_org_non_member():
    """Test is_member_of_org for non-member."""
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    assert is_member_of_org(uuid.uuid4(), user) is False


def test_is_member_of_org_db_fallback_disabled():
    """Test is_member_of_org with DB fallback disabled."""
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    assert is_member_of_org(uuid.uuid4(), user, allow_db_fallback=False) is False


def test_can_manage_org_effective_superadmin():
    """Test can_manage_org_effective for superadmin."""
    user = {"id": str(uuid.uuid4()), "is_superadmin": True, "memberships_by_org": {}}
    assert can_manage_org_effective(uuid.uuid4(), user) is True


def test_can_manage_org_effective_no_user():
    """Test can_manage_org_effective with no user."""
    assert can_manage_org_effective(uuid.uuid4(), None) is False


def test_can_manage_org_effective_member():
    """Test can_manage_org_effective for member with manage permissions."""
    org_id = str(uuid.uuid4())
    user = {
        "id": str(uuid.uuid4()),
        "is_superadmin": False,
        "memberships_by_org": {
            org_id: {"role": "admin", "can_read": True, "can_write": True}
        }
    }
    assert can_manage_org_effective(org_id, user) is True


def test_can_manage_org_effective_non_manager():
    """Test can_manage_org_effective for member without manage permissions."""
    org_id = str(uuid.uuid4())
    user = {
        "id": str(uuid.uuid4()),
        "is_superadmin": False,
        "memberships_by_org": {
            org_id: {"role": "editor", "can_read": True, "can_write": True}
        }
    }
    assert can_manage_org_effective(org_id, user) is False


def test_can_move_scope_to_public():
    """Test can_move_scope to public (only superadmin allowed)."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "is_superadmin": False,
        "memberships_by_org": {
            org_id: {"role": "editor", "can_read": True, "can_write": True}
        }
    }
    
    class R: 
        visibility_scope="organization"
        organization_id=uuid.UUID(org_id)
        owner_user_id=user_id
    
    # Regular users cannot move to public
    assert can_move_scope(R(), "public", None, user) is False
    
    # But superadmin can
    user["is_superadmin"] = True
    assert can_move_scope(R(), "public", None, user) is True


def test_can_move_scope_unauthorized():
    """Test can_move_scope without authorization."""
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    
    class R:
        visibility_scope="organization" 
        organization_id=uuid.uuid4()
        owner_user_id=str(uuid.uuid4())
    
    assert can_move_scope(R(), "organization", uuid.uuid4(), user) is False


def test_can_move_scope_no_user():
    """Test can_move_scope with no user."""
    class R:
        visibility_scope="organization"
        organization_id=uuid.uuid4() 
        owner_user_id=str(uuid.uuid4())
    
    assert can_move_scope(R(), "public", None, None) is False


def test_can_move_scope_invalid_scope():
    """Test can_move_scope with invalid scope."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "is_superadmin": False,
        "memberships_by_org": {
            org_id: {"role": "owner", "can_read": True, "can_write": True}
        }
    }
    
    class R:
        visibility_scope="organization"
        organization_id=uuid.UUID(org_id)
        owner_user_id=user_id
    
    assert can_move_scope(R(), "invalid_scope", None, user) is False


def test_permissions_with_none_resource():
    """Test permission functions handle None resource gracefully."""
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    
    assert can_read(None, user) is False
    assert can_write(None, user) is False


def test_permissions_with_missing_attributes():
    """Test permission functions with incomplete resource objects."""
    user = {"id": str(uuid.uuid4()), "is_superadmin": False, "memberships_by_org": {}}
    
    # Resource missing required attributes
    incomplete_resource = Mock(spec=[])
    
    assert can_read(incomplete_resource, user) is False
    assert can_write(incomplete_resource, user) is False
