"""
API dependency helpers.

Provides dependency-resolved user context and scope information for routes.
"""
import uuid
from typing import Optional, Tuple, Dict, Any
from fastapi import Query

from fastapi import Header, HTTPException, status, Depends
import os
from sqlalchemy import text as _sql_text
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.db import models
from core.db.scope_utils import ScopeContext
from core.db.repositories import tokens as token_repo
from core.utils.token_crypto import parse_token, verify_secret
from core.services.beta_access_service import BetaAccessService
from fastapi import HTTPException
import logging

# Contract:
# Returns (sqlalchemy User model, current_user_context_dict)
# Raises 401 if identity cannot be resolved.

def get_current_user_context(
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
) -> Tuple[Any, Dict[str, Any]]:
    import os
    
    # Check for dev mode first
    is_dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    
    if is_dev_mode:
        # In dev mode, use dev@localhost user
        email = "dev@localhost"
        name = "Development User"
    else:
        # Normal mode: resolve from OAuth2 proxy headers
        name, email = resolve_identity_from_headers(
            x_auth_request_user=x_auth_request_user,
            x_auth_request_email=x_auth_request_email,
            x_forwarded_user=x_forwarded_user,
            x_forwarded_email=x_forwarded_email,
        )
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_or_create_user(db, email=email, display_name=name)
    
    # Check beta access status and send invitation if needed
    if user.beta_access_status == 'pending':
        # Check if user already has a pending request
        from core.db.repositories import beta_access as beta_repo
        existing_request = beta_repo.get_beta_access_request_by_email(db, user.email)
        if not existing_request or existing_request.status != 'pending':
            # Send invitation email for users without beta access who haven't requested it yet
            try:
                from core.services.notification_service import NotificationService
                notification_service = NotificationService(db)
                notification_service.notify_beta_access_invitation(user.email)
            except Exception as e:
                # Log error but don't fail authentication
                logging.getLogger("hindsight.auth").warning(f"Failed to send beta access invitation to {user.email}: {e}")
    
    # Comment out automatic superadmin privileges for dev user to test non-superadmin functionality
    # if is_dev_mode and email == "dev@localhost" and not user.is_superadmin:
    #     user.is_superadmin = True
    #     db.commit()
    #     db.refresh(user)
    
    memberships = get_user_memberships(db, user.id)
    # Normalize keys to string to align with permission helpers that cast org_id to str
    memberships_by_org = {str(m["organization_id"]): m for m in memberships}
    current_user = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_superadmin": bool(getattr(user, "is_superadmin", False)),
        "beta_access_status": user.beta_access_status,
        "memberships": memberships,
        "memberships_by_org": memberships_by_org,
    }
    return user, current_user

# Internal alias used by some modules.
_require_current_user = get_current_user_context

# Legacy helper that returns only the ORM user.
def get_current_user_or_oauth(
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, _ctx = get_current_user_context(
        db=db,
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    return user


def get_current_user_context_or_pat(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
) -> Tuple[Any, Dict[str, Any]]:
    """Return current user context, accepting either oauth2-proxy headers or PAT.

    If a PAT is provided via Authorization: Bearer or X-API-Key, validate and
    load its user; otherwise fallback to oauth2-proxy header flow.
    """
    # Prefer PAT if present
    pat_token = None
    if authorization and authorization.lower().startswith("bearer "):
        pat_token = authorization[7:].strip()
    elif x_api_key:
        pat_token = x_api_key.strip()

    if pat_token:
        parsed = parse_token(pat_token)
        if not parsed:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
        pat = token_repo.get_by_token_id(db, token_id=parsed.token_id)
        if not pat:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        # Status/expiry checks
        if pat.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token not active")
        if pat.expires_at is not None:
            from datetime import datetime, timezone
            if datetime.now(timezone.utc) > pat.expires_at:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
        # Verify secret
        if not verify_secret(parsed.secret, pat.token_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Load user and memberships
        user = db.query(models.User).filter(models.User.id == pat.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token user")
        memberships = get_user_memberships(db, user.id)
        memberships_by_org = {str(m["organization_id"]): m for m in memberships}
        current_user = {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "is_superadmin": bool(getattr(user, "is_superadmin", False)),
            "memberships": memberships,
            "memberships_by_org": memberships_by_org,
            # PAT metadata for downstream checks
            "pat": {
                "id": pat.id,
                "token_id": pat.token_id,
                "scopes": list(pat.scopes or []),
                "organization_id": pat.organization_id,
            },
        }
        # Update last_used timestamp (best-effort)
        try:
            token_repo.mark_used_now(db, pat=pat)
        except Exception:
            pass
        return user, current_user

    # Fallback to oauth2-proxy headers (including DEV_MODE path inside)
    return get_current_user_context(
        db=db,
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )


def ensure_pat_allows_write(current_user: Dict[str, Any], target_org_id=None):
    """Raise 403 if a PAT is present and does not allow write to the target org.

    If no PAT present, this is a no-op.
    """
    if not current_user:
        return
    pat = current_user.get("pat")
    if not pat:
        return
    scopes = set((pat.get("scopes") or []))
    if "write" not in scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token lacks write scope")
    pat_org = pat.get("organization_id")
    # If token has an org restriction and it conflicts with the requested target org, reject
    if pat_org and target_org_id and str(pat_org) != str(target_org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token organization restriction mismatch")

    # Enforce the current user's membership permissions as an additional guard: a PAT
    # must not be usable for write if the token's owner currently lacks write on the
    # effective organization. Determine effective org (target_org_id preferred, else token org)
    effective_org = target_org_id or pat_org
    if effective_org:
        memberships_by_org = current_user.get("memberships_by_org")
        # Only enforce membership-based checks when the effective org entry is
        # actually present in the memberships map. This avoids failing tests and
        # contexts that provide an empty memberships_by_org placeholder.
        if memberships_by_org and str(effective_org) in memberships_by_org:
            mem = memberships_by_org.get(str(effective_org))
            if not mem.get("can_write"):
                # Emit a lightweight audit/log entry for denied PAT usage due to membership drift
                logging.getLogger("hindsight.pat").warning(
                    "PAT denied: user=%s org=%s reason=%s",
                    current_user.get("email"), str(effective_org), "user lacks can_write",
                )
                # deny if the user no longer has write permission on the organization
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token user lacks write permission for organization")


def ensure_pat_allows_read(current_user: Dict[str, Any], target_org_id=None, *, write_implies_read: bool = True):
    """Raise 403 if a PAT is present and does not allow read to the target org.

    - Requires `read` scope, or `write` if `write_implies_read=True`.
    - If PAT has `organization_id`, enforce it matches the target org (when provided).
    - If no PAT present, this is a no-op.
    """
    if not current_user:
        return
    pat = current_user.get("pat")
    if not pat:
        return
    scopes = set((pat.get("scopes") or []))
    has_read = ("read" in scopes) or (write_implies_read and "write" in scopes)
    if not has_read:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token lacks read scope")
    pat_org = pat.get("organization_id")
    # If token has an org restriction and it conflicts with the requested target org, reject
    if pat_org and target_org_id and str(pat_org) != str(target_org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token organization restriction mismatch")

    # Enforce user's current membership read permission. If write implies read and the
    # token has write scope, prefer checking can_write when applicable.
    effective_org = target_org_id or pat_org
    if effective_org:
        memberships_by_org = current_user.get("memberships_by_org")
        # Only enforce membership-based checks when the effective org entry is
        # actually present in the memberships map.
        if memberships_by_org and str(effective_org) in memberships_by_org:
            mem = memberships_by_org.get(str(effective_org))
            # Decide required flag: if token has write and write implies read, treat can_write as acceptable
            scopes = set((pat.get("scopes") or []))
            requires_read_flag = True
            if write_implies_read and "write" in scopes:
                requires_read_flag = False  # we'll allow can_write in place of can_read
            if requires_read_flag and not mem.get("can_read"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token user lacks read permission for organization")
            if not requires_read_flag and not (mem.get("can_read") or mem.get("can_write")):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token user lacks read/write permission for organization")


def get_scope_context(
    db: Session = Depends(get_db),
    # Optional incoming hints (query params)
    scope: Optional[str] = Query(default=None),
    organization_id: Optional[str] = Query(default=None),
    # Explicit scope headers (preferred when present)
    x_active_scope: Optional[str] = Header(default=None, alias="X-Active-Scope"),
    x_organization_id: Optional[str] = Header(default=None, alias="X-Organization-Id"),
    # Headers for PAT or oauth2-proxy
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
) -> ScopeContext:
    """Derive a canonical ScopeContext for the request.

    Rules:
    - If PAT present: if PAT has organization_id -> force organization scope; otherwise default to personal.
      Query hints (scope/org) may be used when safe but can never broaden beyond PAT restrictions.
    - If no PAT: if oauth2 user present -> default personal; else default public.
      Query hints may narrow to organization/public, final filtering enforced by repository layer.
    """
    # Normalize requested scope string
    # Prefer explicit headers if provided; otherwise fall back to query params
    requested_scope = (x_active_scope or scope or '').strip().lower() or None
    requested_org_uuid = None
    org_hint = x_organization_id or organization_id
    if org_hint:
        try:
            requested_org_uuid = uuid.UUID(str(org_hint))
        except Exception:
            requested_org_uuid = None

    # If PAT provided, derive from PAT (authoritative)
    if authorization or x_api_key:
        try:
            user, current_user = get_current_user_context_or_pat(
                db=db,
                authorization=authorization,
                x_api_key=x_api_key,
                x_auth_request_user=x_auth_request_user,
                x_auth_request_email=x_auth_request_email,
                x_forwarded_user=x_forwarded_user,
                x_forwarded_email=x_forwarded_email,
            )
        except HTTPException:
            # invalid PAT → bubble as unauthenticated scope (public)
            return ScopeContext(scope="public", organization_id=None)

        pat = current_user.get("pat") or {}
        pat_org = pat.get("organization_id")
        if pat_org:
            # Force organization scope by PAT restriction; ignore conflicting hints
            try:
                pat_org_uuid = uuid.UUID(str(pat_org))
            except Exception:
                pat_org_uuid = None
            return ScopeContext(scope="organization", organization_id=pat_org_uuid)
        # No org restriction in PAT → accept requested scope when sensible; default to personal
        if requested_scope in {"organization", "public", "personal"}:
            if requested_scope == "organization":
                ctx = ScopeContext(scope="organization", organization_id=requested_org_uuid)
            else:
                ctx = ScopeContext(scope=requested_scope, organization_id=None)
        else:
            ctx = ScopeContext(scope="personal", organization_id=None)
        # Optionally set RLS GUCs for PAT contexts
        try:
            if os.getenv('HINDSIGHT_ENABLE_RLS', 'false').lower() == 'true':
                try:
                    db.execute(_sql_text("SET LOCAL hindsight.enable_rls = 'on'"))
                except Exception:
                    pass
                try:
                    db.execute(_sql_text("SET LOCAL hindsight.user_id = :uid"), {"uid": str(current_user.get('id'))})
                except Exception:
                    pass
                if ctx.scope == 'organization' and ctx.organization_id:
                    try:
                        db.execute(_sql_text("SET LOCAL hindsight.org_id = :oid"), {"oid": str(ctx.organization_id)})
                    except Exception:
                        pass
        except Exception:
            pass
        return ctx

    # No PAT → try oauth2 headers to decide default
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if requested_scope in {"organization", "public", "personal"}:
        ctx = ScopeContext(scope="organization", organization_id=requested_org_uuid) if requested_scope == "organization" else ScopeContext(scope=requested_scope, organization_id=None)
        # We don't have a user id reliably in non-PAT contexts; only set org_id GUC when org scope
        try:
            if os.getenv('HINDSIGHT_ENABLE_RLS', 'false').lower() == 'true':
                try:
                    db.execute(_sql_text("SET LOCAL hindsight.enable_rls = 'on'"))
                except Exception:
                    pass
                if ctx.scope == 'organization' and ctx.organization_id:
                    try:
                        db.execute(_sql_text("SET LOCAL hindsight.org_id = :oid"), {"oid": str(ctx.organization_id)})
                    except Exception:
                        pass
        except Exception:
            pass
        return ctx

    # Default based on presence of user identity
    if email:
        ctx = ScopeContext(scope="personal", organization_id=None)
    else:
        ctx = ScopeContext(scope="public", organization_id=None)
    try:
        if os.getenv('HINDSIGHT_ENABLE_RLS', 'false').lower() == 'true':
            try:
                db.execute(_sql_text("SET LOCAL hindsight.enable_rls = 'on'"))
            except Exception:
                pass
    except Exception:
        pass
    return ctx


def _parse_uuid_maybe(val: Optional[str]):
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except Exception:
        return None


def get_current_user_context_or_guest(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    """Return current user context if authenticated via PAT or oauth2 headers; otherwise (guest) return (None, None).

    This is a permissive variant used for read endpoints that allow guest access.
    """
    try:
        return get_current_user_context_or_pat(
            db=db,
            authorization=authorization,
            x_api_key=x_api_key,
            x_auth_request_user=x_auth_request_user,
            x_auth_request_email=x_auth_request_email,
            x_forwarded_user=x_forwarded_user,
            x_forwarded_email=x_forwarded_email,
        )
    except HTTPException as e:
        # If token provided but invalid, propagate; otherwise treat as guest
        has_pat = bool(authorization or x_api_key)
        if has_pat:
            raise
        return None, None


def get_scoped_user_and_context(
    scope_ctx: ScopeContext = Depends(get_scope_context),
    user_ctx = Depends(get_current_user_context_or_guest),
    # Also accept the raw query hint to enforce PAT/org mismatch when requested explicitly
    organization_id: Optional[str] = Query(default=None),
):
    """Return a tuple (user, current_user, scope_ctx) for endpoints.

    Enforces PAT-org mismatch when a conflicting organization_id query param is provided.
    """
    user, current_user = user_ctx
    # If PAT is present and request hinted a different org, raise 403
    if current_user and current_user.get("pat") and current_user["pat"].get("organization_id") and organization_id:
        pat_org = str(current_user["pat"]["organization_id"])  # store may be UUID or str
        req_org = _parse_uuid_maybe(organization_id)
        if req_org is not None and str(req_org) != str(pat_org):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token organization restriction mismatch")
    return user, current_user, scope_ctx
