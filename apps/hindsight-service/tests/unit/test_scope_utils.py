"""
Tests for core.db.scope_utils module.

This module tests the scope filtering utilities that provide
data governance and access control functionality.
"""
import uuid
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Query

from core.db.scope_utils import (
    get_user_organization_ids,
    apply_scope_filter,
    apply_optional_scope_narrowing,
    validate_scope_access,
    get_scoped_query_filters,
)
from core.api.deps import CurrentUserContext


def _make_user(uid=None, is_superadmin=False, memberships=None, memberships_by_org=None):
    """Build a CurrentUserContext for tests."""
    return CurrentUserContext(
        id=uid or uuid.uuid4(),
        email="",
        display_name=None,
        is_superadmin=is_superadmin,
        is_beta_access_admin=False,
        memberships=memberships or [],
        memberships_by_org=memberships_by_org or {},
        beta_access_status=None,
    )


class TestGetUserOrganizationIds:
    """Test get_user_organization_ids function."""

    def test_none_user_returns_empty_list(self):
        """Test that None user returns empty list."""
        result = get_user_organization_ids(None)
        assert result == []

    def test_empty_user_returns_empty_list(self):
        """Test that user with no memberships returns empty list."""
        result = get_user_organization_ids(_make_user())
        assert result == []

    def test_user_without_memberships_returns_empty_list(self):
        """Test that user without memberships returns empty list."""
        user = _make_user(uid=uuid.uuid4())
        result = get_user_organization_ids(user)
        assert result == []

    def test_user_with_empty_memberships_returns_empty_list(self):
        """Test that user with empty memberships list returns empty list."""
        user = _make_user(memberships=[])
        result = get_user_organization_ids(user)
        assert result == []

    def test_user_with_valid_memberships_returns_org_ids(self):
        """Test that user with valid memberships returns organization IDs."""
        org1_id = uuid.uuid4()
        org2_id = uuid.uuid4()
        user = _make_user(memberships=[
            {'organization_id': str(org1_id)},
            {'organization_id': str(org2_id)},
        ])
        result = get_user_organization_ids(user)
        assert len(result) == 2
        assert org1_id in result
        assert org2_id in result

    def test_user_with_invalid_org_id_skips_invalid(self):
        """Test that invalid organization IDs are skipped."""
        valid_org_id = uuid.uuid4()
        user = _make_user(memberships=[
            {'organization_id': str(valid_org_id)},
            {'organization_id': 'invalid-uuid'},
            {'organization_id': None},
            {},  # No organization_id key
        ])
        result = get_user_organization_ids(user)
        assert len(result) == 1
        assert valid_org_id in result

    def test_user_with_none_memberships_handles_gracefully(self):
        """Test that None memberships are handled gracefully (via empty list)."""
        user = _make_user(memberships=[])
        result = get_user_organization_ids(user)
        assert result == []


class TestApplyScopeFilter:
    """Test apply_scope_filter function."""

    @patch('core.db.scope_utils.or_')
    def test_none_user_filters_to_public_only(self, mock_or):
        """Test that None user can only see public data."""
        mock_query = Mock(spec=Query)
        mock_model = Mock()

        apply_scope_filter(mock_query, None, mock_model)
        mock_query.filter.assert_called_once()

    def test_superadmin_user_sees_everything(self):
        """Test that superadmin user sees everything without filters."""
        mock_query = Mock(spec=Query)
        mock_model = Mock()
        user = _make_user(is_superadmin=True)

        result = apply_scope_filter(mock_query, user, mock_model)
        assert result == mock_query
        mock_query.filter.assert_not_called()

    @patch('core.db.scope_utils.or_')
    def test_regular_user_gets_scoped_filter(self, mock_or):
        """Test that regular user gets proper scope filtering."""
        mock_query = Mock(spec=Query)
        mock_model = Mock()
        org_id = uuid.uuid4()
        user = _make_user(memberships=[{'organization_id': str(org_id)}])

        apply_scope_filter(mock_query, user, mock_model)
        mock_query.filter.assert_called_once()

    @patch('core.db.scope_utils.or_')
    def test_user_without_organizations_gets_personal_and_public_only(self, mock_or):
        """Test that user without organizations can only see personal and public data."""
        mock_query = Mock(spec=Query)
        mock_model = Mock()
        user = _make_user(memberships=[])

        apply_scope_filter(mock_query, user, mock_model)
        mock_query.filter.assert_called_once()

    @patch('core.db.scope_utils.or_')
    def test_user_with_malformed_data_handled_gracefully(self, mock_or):
        """Test that users with empty memberships are handled gracefully."""
        mock_query = Mock(spec=Query)
        mock_model = Mock()
        user = _make_user()  # No memberships

        apply_scope_filter(mock_query, user, mock_model)
        mock_query.filter.assert_called_once()


class TestApplyOptionalScopeNarrowing:
    """Test apply_optional_scope_narrowing function."""

    def test_no_filters_returns_original_query(self):
        """Test that no filters returns original query."""
        mock_query = Mock(spec=Query)
        mock_model = Mock()

        result = apply_optional_scope_narrowing(
            mock_query, None, None, mock_model
        )
        assert result == mock_query

    def test_valid_scope_filter_applies(self):
        """Test that valid scope filters are applied."""
        for scope in ['personal', 'organization', 'public']:
            query_mock = Mock(spec=Query)
            query_mock.filter.return_value = query_mock
            mock_model = Mock()

            result = apply_optional_scope_narrowing(
                query_mock, scope, None, mock_model
            )
            query_mock.filter.assert_called_once()

    def test_invalid_scope_filter_ignored(self):
        """Test that invalid scope filters are ignored."""
        mock_query = Mock(spec=Query)
        mock_model = Mock()

        result = apply_optional_scope_narrowing(
            mock_query, 'invalid_scope', None, mock_model
        )
        assert result == mock_query

    def test_organization_id_filter_applies(self):
        """Test that organization ID filter is applied."""
        org_id = uuid.uuid4()
        query_mock = Mock(spec=Query)
        query_mock.filter.return_value = query_mock
        mock_model = Mock()

        result = apply_optional_scope_narrowing(
            query_mock, None, org_id, mock_model
        )
        query_mock.filter.assert_called_once()

    def test_both_filters_apply(self):
        """Test that both scope and organization filters apply."""
        org_id = uuid.uuid4()
        query_mock = Mock(spec=Query)
        query_mock.filter.return_value = query_mock
        mock_model = Mock()

        result = apply_optional_scope_narrowing(
            query_mock, 'organization', org_id, mock_model
        )
        assert query_mock.filter.call_count == 2


class TestValidateScopeAccess:
    """Test validate_scope_access function."""

    def test_none_user_can_only_access_public(self):
        """Test that None user can only access public scope."""
        assert validate_scope_access(None, 'public') is True
        assert validate_scope_access(None, 'personal') is False
        assert validate_scope_access(None, 'organization') is False

    def test_superadmin_can_access_everything(self):
        """Test that superadmin can access all scopes."""
        user = _make_user(is_superadmin=True)
        assert validate_scope_access(user, 'public') is True
        assert validate_scope_access(user, 'personal') is True
        assert validate_scope_access(user, 'organization') is True

    def test_public_scope_accessible_to_all_users(self):
        """Test that public scope is accessible to all users."""
        user = _make_user()
        assert validate_scope_access(user, 'public') is True

    def test_personal_scope_only_accessible_to_owner(self):
        """Test that personal scope is only accessible to the owner."""
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        user = _make_user(uid=user_id)

        assert validate_scope_access(user, 'personal', owner_user_id=user_id) is True
        assert validate_scope_access(user, 'personal', owner_user_id=other_user_id) is False

    def test_organization_scope_accessible_to_members(self):
        """Test that organization scope is accessible to organization members."""
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        other_org_id = uuid.uuid4()
        user = _make_user(
            uid=user_id,
            memberships=[{'organization_id': str(org_id)}],
        )

        assert validate_scope_access(user, 'organization', organization_id=org_id) is True
        assert validate_scope_access(user, 'organization', organization_id=other_org_id) is False

    def test_organization_scope_without_org_id_returns_false(self):
        """Test that organization scope without organization ID returns False."""
        user = _make_user()
        assert validate_scope_access(user, 'organization', organization_id=None) is False

    def test_invalid_scope_returns_false(self):
        """Test that invalid scope returns False."""
        user = _make_user()
        assert validate_scope_access(user, 'invalid_scope') is False

    def test_user_without_memberships_cannot_access_org_scope(self):
        """Test that user without memberships cannot access organization scope."""
        user = _make_user(memberships=[])
        org_id = uuid.uuid4()
        assert validate_scope_access(user, 'organization', organization_id=org_id) is False


class TestGetScopedQueryFilters:
    """Test get_scoped_query_filters function."""

    def test_returns_filter_dict(self):
        """Test that function returns filter dictionary."""
        user = _make_user()
        scope = 'personal'
        org_id = uuid.uuid4()

        result = get_scoped_query_filters(user, scope, org_id)

        assert isinstance(result, dict)
        assert result['current_user'] == user
        assert result['scope'] == scope
        assert result['organization_id'] == org_id

    def test_handles_none_values(self):
        """Test that function handles None values correctly."""
        result = get_scoped_query_filters(None, None, None)

        assert isinstance(result, dict)
        assert result['current_user'] is None
        assert result['scope'] is None
        assert result['organization_id'] is None

    def test_partial_parameters(self):
        """Test that function works with partial parameters."""
        user = _make_user()

        result = get_scoped_query_filters(user)

        assert result['current_user'] == user
        assert result['scope'] is None
        assert result['organization_id'] is None
