"""
Scope filtering utilities for data governance.

This module provides reusable functions for applying scope-based access control
to database queries, eliminating code duplication across CRUD operations.
"""
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from . import models


def get_user_organization_ids(current_user: Optional[Dict[str, Any]]) -> List[uuid.UUID]:
    """Extract organization IDs that the user has access to."""
    if not current_user:
        return []

    org_ids = []
    try:
        for membership in current_user.get('memberships', []):
            org_id_str = membership.get('organization_id')
            if org_id_str:
                try:
                    org_ids.append(uuid.UUID(org_id_str))
                except (ValueError, TypeError):
                    continue
    except (AttributeError, TypeError):
        pass

    return org_ids


def apply_scope_filter(query, current_user: Optional[Dict[str, Any]], model_class):
    """
    Apply scope-based filtering to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        current_user: User context dict or None for guests
        model_class: The model class (Agent, MemoryBlock, etc.)

    Returns:
        Filtered query
    """
    if current_user is None:
        # Guests can only see public data
        return query.filter(model_class.visibility_scope == 'public')

    # Superadmin sees everything
    if current_user.get('is_superadmin'):
        return query

    user_id = current_user.get('id')
    org_ids = get_user_organization_ids(current_user)

    return query.filter(
        or_(
            model_class.visibility_scope == 'public',
            model_class.owner_user_id == user_id,
            and_(
                model_class.visibility_scope == 'organization',
                model_class.organization_id.in_(org_ids) if org_ids else False,
            ),
        )
    )


def apply_optional_scope_narrowing(query, scope: Optional[str], organization_id: Optional[uuid.UUID], model_class):
    """
    Apply optional scope narrowing filters to a query.

    Args:
        query: SQLAlchemy query object
        scope: Optional scope filter ('personal', 'organization', 'public')
        organization_id: Optional organization ID filter
        model_class: The model class

    Returns:
        Filtered query
    """
    if scope in ('personal', 'organization', 'public'):
        query = query.filter(model_class.visibility_scope == scope)

    if organization_id is not None:
        query = query.filter(model_class.organization_id == organization_id)

    return query


def validate_scope_access(current_user: Optional[Dict[str, Any]],
                         visibility_scope: str,
                         organization_id: Optional[uuid.UUID] = None,
                         owner_user_id: Optional[uuid.UUID] = None) -> bool:
    """
    Validate if a user can access a specific scope/ownership combination.

    Args:
        current_user: User context dict or None
        visibility_scope: The scope ('personal', 'organization', 'public')
        organization_id: Organization ID for organization scope
        owner_user_id: Owner user ID for personal scope

    Returns:
        True if access is allowed
    """
    if current_user is None:
        return visibility_scope == 'public'

    if current_user.get('is_superadmin'):
        return True

    user_id = current_user.get('id')

    if visibility_scope == 'public':
        return True
    elif visibility_scope == 'personal':
        return owner_user_id == user_id
    elif visibility_scope == 'organization':
        if not organization_id:
            return False
        org_ids = get_user_organization_ids(current_user)
        return organization_id in org_ids

    return False


def get_scoped_query_filters(current_user: Optional[Dict[str, Any]],
                           scope: Optional[str] = None,
                           organization_id: Optional[uuid.UUID] = None):
    """
    Get the filters needed for a scoped query.

    Returns a dict with 'base_filters' and 'narrowing_filters' that can be
    applied to any scoped model query.
    """
    return {
        'current_user': current_user,
        'scope': scope,
        'organization_id': organization_id,
    }
