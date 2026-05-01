"""Tests for the CurrentUserContext dataclass and PatContext shape contract.

Replaces the legacy `Dict[str, Any]` shape introduced by issue #69. These
tests pin the dataclass contract so a future field rename or removal
breaks the test rather than silently degrading consumers.
"""
import dataclasses
import pytest
from uuid import uuid4

from core.api.deps import CurrentUserContext, PatContext


def test_current_user_context_has_required_fields():
    """All 8 always-required fields must be settable; defaults exist for pat/dev_mode_pat."""
    user_id = uuid4()
    ctx = CurrentUserContext(
        id=user_id,
        email="user@example.com",
        display_name="User",
        is_superadmin=False,
        is_beta_access_admin=False,
        memberships=[],
        memberships_by_org={},
        beta_access_status="accepted",
    )

    assert ctx.id == user_id
    assert ctx.email == "user@example.com"
    assert ctx.display_name == "User"
    assert ctx.is_superadmin is False
    assert ctx.is_beta_access_admin is False
    assert ctx.memberships == []
    assert ctx.memberships_by_org == {}
    assert ctx.beta_access_status == "accepted"
    assert ctx.pat is None
    assert ctx.dev_mode_pat is None


def test_current_user_context_is_frozen():
    """Attempted mutation must raise — protects against accidental privilege change."""
    ctx = CurrentUserContext(
        id=uuid4(),
        email="x@y.z",
        display_name=None,
        is_superadmin=False,
        is_beta_access_admin=False,
        memberships=[],
        memberships_by_org={},
        beta_access_status=None,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.is_superadmin = True  # type: ignore[misc]


def test_current_user_context_attribute_typo_raises():
    """The whole point: a typo on attribute access fails LOUDLY, unlike .get() which silently returns None."""
    ctx = CurrentUserContext(
        id=uuid4(),
        email="x@y.z",
        display_name=None,
        is_superadmin=True,
        is_beta_access_admin=False,
        memberships=[],
        memberships_by_org={},
        beta_access_status=None,
    )

    with pytest.raises(AttributeError):
        _ = ctx.is_superadmnin  # noqa — intentional typo to prove the failure mode


def test_pat_context_has_required_fields():
    """PatContext shape contract."""
    pat_id = uuid4()
    pat = PatContext(
        id=pat_id,
        token_id="tok_123",
        scopes=["read", "write"],
        organization_id=None,
    )

    assert pat.id == pat_id
    assert pat.token_id == "tok_123"
    assert pat.scopes == ["read", "write"]
    assert pat.organization_id is None


def test_current_user_context_with_pat():
    """Composing CurrentUserContext with a PatContext."""
    pat = PatContext(id=uuid4(), token_id="tok", scopes=["read"], organization_id=None)
    ctx = CurrentUserContext(
        id=uuid4(),
        email="x@y.z",
        display_name=None,
        is_superadmin=False,
        is_beta_access_admin=False,
        memberships=[],
        memberships_by_org={},
        beta_access_status=None,
        pat=pat,
    )

    assert ctx.pat is pat
    assert ctx.pat.scopes == ["read"]
