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
