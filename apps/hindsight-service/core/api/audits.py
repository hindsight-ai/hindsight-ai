from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models, schemas, crud
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.api.permissions import can_manage_org

router = APIRouter(tags=["audits"])

def _require_current_user(db: Session,
                          x_auth_request_user: Optional[str],
                          x_auth_request_email: Optional[str],
                          x_forwarded_user: Optional[str],
                          x_forwarded_email: Optional[str]):
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_or_create_user(db, email=email, display_name=name)
    # Build a compact context with memberships_by_org
    memberships = get_user_memberships(db, user.id)
    memberships_by_org = {m["organization_id"]: m for m in memberships}
    current_user = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_superadmin": bool(user.is_superadmin),
        "memberships": memberships,
        "memberships_by_org": memberships_by_org,
    }
    return user, current_user

@router.get("/", response_model=List[schemas.AuditLog])
def list_audit_logs(
    organization_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)

    if organization_id:
        if not can_manage_org(organization_id, current_user):
            raise HTTPException(status_code=403, detail="Forbidden")
    elif not current_user.get('is_superadmin'):
        raise HTTPException(status_code=403, detail="Forbidden, organization_id is required for non-superadmins")

    audit_logs = crud.get_audit_logs(db, organization_id=organization_id, user_id=user_id, skip=skip, limit=limit)
    # Adapt SQLAlchemy objects: schema expects .metadata (dict) but model uses metadata_json column
    adapted = []
    for log in audit_logs:
        # Create a lightweight shim object with attribute 'metadata'
        if getattr(log, 'metadata_json', None) is not None:
            setattr(log, 'metadata', log.metadata_json)
        else:
            setattr(log, 'metadata', None)
        adapted.append(log)
    return adapted
