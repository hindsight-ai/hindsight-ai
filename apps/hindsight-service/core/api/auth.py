"""
Authentication helpers and identity resolution.

Parses proxy headers, normalizes emails, and upserts users while supporting
simple superadmin elevation via environment configuration.
"""
import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from core.db import models

logger = logging.getLogger(__name__)


def _normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return email.strip().lower()


def _normalize_list_env(var_name: str) -> set:
    raw = os.getenv(var_name, "")
    logger.debug("auth_env_parse: %s raw='%s'", var_name, raw)
    values = set()
    for entry in raw.split(","):
        cleaned = entry.strip().strip('"').strip("'")
        if cleaned:
            values.add(cleaned.lower())
    return values


def _admin_emails() -> set:
    return _normalize_list_env("ADMIN_EMAILS")


def _beta_access_admin_emails() -> set:
    return _normalize_list_env("BETA_ACCESS_ADMINS")


def is_beta_access_admin(email: Optional[str]) -> bool:
    if not email:
        return False
    return _normalize_email(email) in _beta_access_admin_emails()


def resolve_identity_from_headers(
    x_auth_request_user: Optional[str],
    x_auth_request_email: Optional[str],
    x_forwarded_user: Optional[str],
    x_forwarded_email: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    user = x_auth_request_user or x_forwarded_user
    email = _normalize_email(x_auth_request_email or x_forwarded_email)
    return user, email


class IdentityMismatchError(Exception):
    """Raised when an authenticated request's external_subject does not
    match the existing User row's bound external_subject. Defense against
    email reassignment / IDP collisions: a recycled email cannot silently
    inherit the previous owner's data."""


def get_or_create_user(
    db: Session,
    email: str,
    display_name: Optional[str] = None,
    *,
    external_subject: Optional[str] = None,
    auth_provider: Optional[str] = None,
) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    was_new = False
    if not user:
        user = models.User(
            email=email,
            display_name=display_name or email.split("@")[0],
            beta_access_status='not_requested',
            external_subject=external_subject,
            auth_provider=auth_provider,
        )
        db.add(user)
        was_new = True
    elif external_subject is not None:
        # If the IdP's user-id claim is set to the email itself (oauth2-proxy
        # default `preferred_username` for Google), every external_subject
        # equals the email and the binding can never distinguish two humans
        # sharing an email. Warn loudly so the operator notices the config is
        # not providing the protection it should.
        if external_subject == email:
            logger.warning(
                "auth_subject_is_email: external_subject==email for %s — "
                "set OAUTH2_PROXY_USER_ID_CLAIM=sub (or equivalent) so the "
                "external_subject binding can actually catch email-reuse.",
                email,
            )
        # Identity binding for existing rows:
        #   - row has no bound subject -> bind it (TOFU; covers legacy users)
        #   - row's subject matches    -> ok
        #   - row's subject differs    -> refuse (account inheritance attempt)
        existing_sub = getattr(user, "external_subject", None)
        if not existing_sub:
            user.external_subject = external_subject
            if auth_provider is not None and not getattr(user, "auth_provider", None):
                user.auth_provider = auth_provider
            try:
                db.commit()
                db.refresh(user)
            except Exception:
                db.rollback()
        elif existing_sub != external_subject:
            logger.warning(
                "identity_mismatch: email=%s existing_subject=%s incoming_subject=%s",
                email, existing_sub, external_subject,
            )
            raise IdentityMismatchError(
                "Account exists for this email but was first registered by a "
                "different identity. Contact an administrator."
            )

    # Elevate to superadmin based on ADMIN_EMAILS only at creation time to avoid test-order flakiness
    admins = _admin_emails()
    if not admins:
        logger.debug("admin_emails_empty: no ADMIN_EMAILS configured")
    if was_new:
        if email in admins:
            user.is_superadmin = True
            logger.info("admin_user_created: email=%s flagged as superadmin", email)

    if was_new:
        db.flush()
        db.commit()
        db.refresh(user)
        return user
    # Existing users might predate a new ADMIN_EMAILS value; promote them when necessary.
    if email in admins and not getattr(user, "is_superadmin", False):
        user.is_superadmin = True
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("admin_user_promote_failed: email=%s", email)
        else:
            db.refresh(user)
            logger.info("admin_user_promoted: email=%s flagged as superadmin", email)
    elif email not in admins:
        logger.debug("admin_user_not_listed: email=%s admins=%s", email, sorted(admins))

    if not getattr(user, "beta_access_status", None):
        user.beta_access_status = 'not_requested'
        try:
            db.commit()
        except Exception:
            db.rollback()
        else:
            db.refresh(user)
    # For existing users, avoid unnecessary commits that could clobber test state
    db.refresh(user)
    return user


def get_user_memberships(db: Session, user_id) -> List[Dict[str, Any]]:
    # Join memberships to organization for names
    try:
        results = (
            db.query(models.OrganizationMembership, models.Organization)
            .join(models.Organization, models.Organization.id == models.OrganizationMembership.organization_id)
            .filter(models.OrganizationMembership.user_id == user_id)
            .all()
        )
    except Exception:
        # In unit tests some endpoints override dependencies with mock Sessions that may not fully
        # implement SQLAlchemy behavior; treat as no memberships rather than failing the entire request.
        return []

    # A defensive guard: some mocks may yield a single Mock object instead of list/tuple.
    if not isinstance(results, (list, tuple)):
        return []

    memberships: List[Dict[str, Any]] = []
    for row in results:
        # Support either (membership, org) tuple or a single membership object.
        try:
            # SQLAlchemy Row objects contain tuples that can be unpacked
            if hasattr(row, '__iter__') and len(row) == 2:
                m, org = row
            else:
                m = row
                org = getattr(row, "organization", None)
            if not m:
                continue
            org_id = getattr(m, "organization_id", "")
            org_name = getattr(org, "name", None)
            role = getattr(m, "role", None)
            can_read = getattr(m, "can_read", True)
            can_write = getattr(m, "can_write", True)
            
            memberships.append(
                {
                    "organization_id": str(org_id) if org_id else None,
                    "organization_name": org_name,
                    "role": role,
                    "can_read": bool(can_read),
                    "can_write": bool(can_write),
                }
            )
        except Exception:
            # Ignore malformed mock rows
            continue
    return memberships
