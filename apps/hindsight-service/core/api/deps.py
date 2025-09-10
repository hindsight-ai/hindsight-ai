import uuid
from typing import Optional, Tuple, Dict, Any

from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships

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
    
    # Ensure dev user has superadmin privileges in dev mode
    if is_dev_mode and email == "dev@localhost" and not user.is_superadmin:
        user.is_superadmin = True
        db.commit()
        db.refresh(user)
    
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
