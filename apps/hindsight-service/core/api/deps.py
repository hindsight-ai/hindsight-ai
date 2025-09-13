"""
API dependency helpers.

Provides dependency-resolved current user context and compatibility shims
used by various route modules and tests.
"""
import uuid
from typing import Optional, Tuple, Dict, Any

from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.db import models
from core.db.repositories import tokens as token_repo
from core.utils.token_crypto import parse_token, verify_secret
from fastapi import HTTPException

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
        "memberships": memberships,
        "memberships_by_org": memberships_by_org,
    }
    return user, current_user

# Backwards compatible alias name some modules used internally.
_require_current_user = get_current_user_context

# Backwards-compat shim used by some integration tests and older routes.
# Historically returned only the ORM user; keep that behavior here.
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
    if pat_org and target_org_id and str(pat_org) != str(target_org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token organization restriction mismatch")
