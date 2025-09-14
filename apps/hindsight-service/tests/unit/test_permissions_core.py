import uuid

from types import SimpleNamespace

from core.api.permissions import (
    get_org_membership,
    can_read,
    can_write,
    can_manage_org,
    can_manage_org_effective,
    is_member_of_org,
    can_move_scope,
)
from core.utils.scopes import SCOPE_PUBLIC, SCOPE_PERSONAL, SCOPE_ORGANIZATION


def _resource(scope, owner=None, org=None):
    return SimpleNamespace(visibility_scope=scope, owner_user_id=owner, organization_id=org)


def test_get_org_membership_from_map_and_list():
    org_id = uuid.uuid4()
    m = {"organization_id": str(org_id), "role": "owner", "can_read": True, "can_write": True}
    user = {"memberships_by_org": {str(org_id): m}, "memberships": [m]}
    assert get_org_membership(org_id, user) == m

    # From list only
    user2 = {"memberships": [m]}
    assert get_org_membership(org_id, user2) == m

    # None / missing
    assert get_org_membership(None, user) is None
    assert get_org_membership(org_id, None) is None


def test_can_read_variants():
    org = uuid.uuid4()
    owner = uuid.uuid4()
    member = {"id": owner, "memberships_by_org": {str(org): {"role": "viewer", "can_read": True}}}

    # Public readable
    assert can_read(_resource(SCOPE_PUBLIC), None) is True

    # Personal only by owner
    assert can_read(_resource(SCOPE_PERSONAL, owner=owner), member) is True
    assert can_read(_resource(SCOPE_PERSONAL, owner=uuid.uuid4()), member) is False

    # Organization by membership (can_read True)
    assert can_read(_resource(SCOPE_ORGANIZATION, org=org), member) is True


def test_can_write_variants():
    org = uuid.uuid4()
    owner = uuid.uuid4()
    member = {"id": owner, "memberships_by_org": {str(org): {"role": "editor", "can_write": True}}}
    nonwriter = {"id": owner, "memberships_by_org": {str(org): {"role": "viewer", "can_write": False}}}

    assert can_write(_resource(SCOPE_PERSONAL, owner=owner), member) is True
    assert can_write(_resource(SCOPE_PERSONAL, owner=uuid.uuid4()), member) is False
    assert can_write(_resource(SCOPE_ORGANIZATION, org=org), member) is True
    assert can_write(_resource(SCOPE_ORGANIZATION, org=org), nonwriter) is False


def test_manage_membership_checks_without_db():
    org = uuid.uuid4()
    admin = {"id": uuid.uuid4(), "memberships_by_org": {str(org): {"role": "admin"}}}
    viewer = {"id": uuid.uuid4(), "memberships_by_org": {str(org): {"role": "viewer"}}}

    assert can_manage_org(org, admin) is True
    assert can_manage_org_effective(org, viewer, allow_db_fallback=False) is False
    assert is_member_of_org(org, admin) is True
    assert is_member_of_org(org, viewer) is True
    assert is_member_of_org(org, {"is_superadmin": True}) is True


def test_can_move_scope_rules():
    org = uuid.uuid4()
    owner = uuid.uuid4()
    admin = {"id": owner, "memberships_by_org": {str(org): {"role": "admin"}}}
    viewer = {"id": owner, "memberships_by_org": {str(org): {"role": "viewer"}}}
    superuser = {"id": owner, "is_superadmin": True}

    res = _resource(SCOPE_PERSONAL, owner=owner)
    assert can_move_scope(res, SCOPE_PERSONAL, None, admin) is True
    assert can_move_scope(res, SCOPE_ORGANIZATION, org, admin) is True
    assert can_move_scope(res, SCOPE_ORGANIZATION, org, viewer) is False
    assert can_move_scope(res, SCOPE_PUBLIC, None, admin) is False
    assert can_move_scope(res, SCOPE_PUBLIC, None, superuser) is True

