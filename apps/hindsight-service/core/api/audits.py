"""
Audit log API endpoints.

Query and present audit logs with permission checks tailored for
organization administrators.
"""
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import schemas, crud
from core.api.deps import get_current_user_context
from core.api.permissions import can_manage_org

router = APIRouter(prefix="/audits", tags=["audits"])

@router.get("/", response_model=List[schemas.AuditLog])
def list_audit_logs(
    organization_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context

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
