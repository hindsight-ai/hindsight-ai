import uuid
import pytest
from core.api.permissions import is_member_of_org, can_manage_org_effective
from core.api.deps import CurrentUserContext
from core.db import models


def _ctx(is_superadmin=False, memberships_by_org=None):
    return CurrentUserContext(
        id=uuid.uuid4(),
        email="",
        display_name=None,
        is_superadmin=is_superadmin,
        is_beta_access_admin=False,
        memberships=[],
        memberships_by_org=memberships_by_org or {},
        beta_access_status=None,
    )


def test_is_member_of_org_context_only():
    """Verify is_member_of_org respects context-only memberships."""
    org_id = "a4e7e61c-1e1a-42f8-8e3c-21a67e206d1d"
    user_context = _ctx(memberships_by_org={org_id: {"role": "member"}})
    assert is_member_of_org(org_id, user_context, allow_db_fallback=False) == True

def test_is_member_of_org_superadmin_bypass():
    """Superadmin should always have membership access."""
    org_id = "a4e7e61c-1e1a-42f8-8e3c-21a67e206d1d"
    user_context = _ctx(is_superadmin=True)
    assert is_member_of_org(org_id, user_context) == True

def test_can_manage_org_effective_superadmin():
    """Superadmin should always have effective management rights."""
    org_id = "a4e7e61c-1e1a-42f8-8e3c-21a67e206d1d"
    user_context = _ctx(is_superadmin=True)
    assert can_manage_org_effective(org_id, user_context) == True

def test_can_manage_org_effective_context_owner():
    """Owner role from context should grant effective management rights."""
    org_id = "a4e7e61c-1e1a-42f8-8e3c-21a67e206d1d"
    user_context = _ctx(memberships_by_org={org_id: {"role": "owner"}})
    assert can_manage_org_effective(org_id, user_context, allow_db_fallback=False) == True

def test_can_manage_org_effective_context_admin():
    """Admin role from context should grant effective management rights."""
    org_id = "a4e7e61c-1e1a-42f8-8e3c-21a67e206d1d"
    user_context = _ctx(memberships_by_org={org_id: {"role": "admin"}})
    assert can_manage_org_effective(org_id, user_context, allow_db_fallback=False) == True

def test_can_manage_org_effective_context_editor_denied():
    """Editor role from context should NOT grant effective management rights."""
    org_id = "a4e7e61c-1e1a-42f8-8e3c-21a67e206d1d"
    user_context = _ctx(memberships_by_org={org_id: {"role": "editor"}})
    assert can_manage_org_effective(org_id, user_context, allow_db_fallback=False) == False
