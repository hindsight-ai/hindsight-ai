import uuid
import pytest

from core.api.auth import resolve_identity_from_headers, get_or_create_user
from core.api.deps import get_scope_context
from core.db.database import get_db_session_local


def test_resolve_identity_and_get_or_create_user(db_session):
    name, email = resolve_identity_from_headers("User", "user@example.com", None, None)
    assert name == "User" and email == "user@example.com"

    # create user and fetch again is idempotent
    user = get_or_create_user(db_session, email=email, display_name=name)
    user2 = get_or_create_user(db_session, email=email, display_name=name)
    assert user.id == user2.id


def test_get_scope_context_paths(db_session):
    # No PAT, with org scope hint
    org = uuid.uuid4()
    ctx = get_scope_context(
        db=db_session,
        scope="organization",
        organization_id=str(org),
        x_active_scope=None,
        x_organization_id=None,
        authorization=None,
        x_api_key=None,
        x_auth_request_user="u",
        x_auth_request_email="e@example.com",
        x_forwarded_user=None,
        x_forwarded_email=None,
    )
    assert ctx.scope == "organization" and ctx.organization_id == org

    # Public scope hint
    ctx2 = get_scope_context(
        db=db_session,
        scope="public",
        organization_id=None,
        x_active_scope=None,
        x_organization_id=None,
        authorization=None,
        x_api_key=None,
        x_auth_request_user=None,
        x_auth_request_email=None,
        x_forwarded_user=None,
        x_forwarded_email=None,
    )
    assert ctx2.scope == "public" and ctx2.organization_id is None

