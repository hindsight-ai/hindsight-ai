"""
Beta access API endpoints.

Manage beta access requests and reviews.
"""
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.api.deps import get_current_user_context
from core.services.beta_access_service import BetaAccessService
from core.db import schemas


router = APIRouter(prefix="/beta-access", tags=["beta-access"])


@router.post("/request", status_code=status.HTTP_201_CREATED)
def request_beta_access(
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    # Resolve email from headers locally to avoid module-level dependency import issues
    from core.api.auth import resolve_identity_from_headers
    # Respect DEV_MODE: only default to dev@localhost when DEV_MODE == "true"
    import os
    is_dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    if is_dev_mode:
        user_email = "dev@localhost"
    else:
        _name, user_email = resolve_identity_from_headers(
            x_auth_request_user=x_auth_request_user,
            x_auth_request_email=x_auth_request_email,
            x_forwarded_user=x_forwarded_user,
            x_forwarded_email=x_forwarded_email,
        )

    if not user_email:
        raise HTTPException(status_code=401, detail="Authentication required")

    service = BetaAccessService(db)
    result = service.request_beta_access(user_id=None, email=user_email)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.post("/review/{request_id}", status_code=status.HTTP_200_OK)
def review_beta_access_request(
    request_id: uuid.UUID,
    decision: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    # TODO: Check if user is admin (e.g., user.email == 'ibarz.jean@gmail.com')
    if user.email != 'ibarz.jean@gmail.com':
        raise HTTPException(status_code=403, detail="Not authorized")

    service = BetaAccessService(db)
    result = service.review_beta_access_request(request_id, decision, user.email, reason, user.id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.get("/status")
def get_beta_access_status(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    service = BetaAccessService(db)
    status = service.get_beta_access_status(user.id)
    return {"status": status}


@router.get("/pending")
def get_pending_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    if user.email != 'ibarz.jean@gmail.com':
        raise HTTPException(status_code=403, detail="Not authorized")

    service = BetaAccessService(db)
    requests = service.get_pending_requests(skip, limit)
    return {"requests": requests}
