"""
Beta access API endpoints.

Manage beta access requests and reviews.
"""
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.api.deps import get_current_user_context
from core.services.beta_access_service import BetaAccessService
from core.db import schemas


router = APIRouter(prefix="/beta-access", tags=["beta-access"])


@router.post("/request", status_code=status.HTTP_201_CREATED)
def request_beta_access(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    service = BetaAccessService(db)
    result = service.request_beta_access(user.id, user.email)
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
    result = service.review_beta_access_request(request_id, decision, user.email, reason)
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
