from core.api import permissions

class Dummy:
    def __init__(self, visibility_scope, owner_user_id=None, organization_id=None):
        self.visibility_scope = visibility_scope
        self.owner_user_id = owner_user_id
        self.organization_id = organization_id


def _ctx(uid, is_super=False, memberships=None):
    memberships = memberships or []
    return {
        "id": uid,
        "is_superadmin": is_super,
        "memberships": memberships,
        "memberships_by_org": {m['organization_id']: m for m in memberships},
    }


def test_can_read_public():
    r = Dummy("public")
    assert permissions.can_read(r, None) is True


def test_personal_read_and_write():
    r = Dummy("personal", owner_user_id="u1")
    assert permissions.can_read(r, _ctx("u1"))
    assert permissions.can_write(r, _ctx("u1"))
    assert not permissions.can_write(r, _ctx("u2"))


def test_org_read_write_roles():
    r = Dummy("organization", organization_id="org1")
    viewer = _ctx("u1", memberships=[{"organization_id": "org1", "role": "viewer", "can_read": True, "can_write": False}])
    editor = _ctx("u2", memberships=[{"organization_id": "org1", "role": "editor", "can_read": True, "can_write": False}])
    admin = _ctx("u3", memberships=[{"organization_id": "org1", "role": "admin", "can_read": True, "can_write": True}])

    assert permissions.can_read(r, viewer)
    assert not permissions.can_write(r, viewer)
    assert permissions.can_write(r, editor)
    assert permissions.can_write(r, admin)


def test_can_manage_org():
    ctx = _ctx("u1", memberships=[{"organization_id": "org1", "role": "admin"}])
    assert permissions.can_manage_org("org1", ctx)
    assert not permissions.can_manage_org("org2", ctx)


def test_can_move_scope():
    res = Dummy("personal", owner_user_id="u1", organization_id=None)
    ctx_owner = _ctx("u1")
    ctx_other = _ctx("u2")
    assert permissions.can_move_scope(res, "personal", None, ctx_owner)
    assert not permissions.can_move_scope(res, "personal", None, ctx_other)

    # Org move requires manage rights
    res_org = Dummy("organization", organization_id="org1")
    ctx_admin = _ctx("u3", memberships=[{"organization_id": "org1", "role": "admin"}])
    assert permissions.can_move_scope(res_org, "organization", "org1", ctx_admin)
    assert not permissions.can_move_scope(res_org, "organization", "org1", ctx_other)

    # Public only superadmin
    super_ctx = _ctx("u4", is_super=True)
    assert permissions.can_move_scope(res_org, "public", None, super_ctx)
    assert not permissions.can_move_scope(res_org, "public", None, ctx_owner)
