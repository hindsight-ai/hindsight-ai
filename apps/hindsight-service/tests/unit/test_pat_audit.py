import uuid
import logging

import pytest

from core.api import deps as deps_mod


def _fake_current_user_with_pat(scopes, org_id=None, can_write=True):
    return {
        "id": uuid.uuid4(),
        "email": "audit@example.com",
        "display_name": "AuditUser",
        "memberships": [],
        "memberships_by_org": {str(org_id): {"can_read": True, "can_write": can_write}} if org_id else {},
        "pat": {"id": uuid.uuid4(), "token_id": "tid", "scopes": scopes, "organization_id": org_id},
    }


def test_pat_denied_emits_audit(caplog):
    caplog.set_level(logging.WARNING, logger="hindsight.pat")
    org = uuid.uuid4()
    cu = _fake_current_user_with_pat(["write"], org_id=org, can_write=False)

    with pytest.raises(Exception):
        deps_mod.ensure_pat_allows_write(cu, target_org_id=org)

    # Assert warning logged
    warnings = [r for r in caplog.records if r.name == "hindsight.pat"]
    assert any("PAT denied" in r.getMessage() for r in warnings)
