"""
Beta access API endpoints.

Manage beta access requests and reviews.
"""
from datetime import datetime
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db.database import get_db
from core.api.deps import get_current_user_context, require_beta_access_admin
from core.services.beta_access_service import BetaAccessService
from core.db import schemas, models
from core.db.repositories import beta_access as beta_repo
from core.audit import audit_log, AuditAction, AuditStatus
from core.utils.runtime import dev_mode_active


router = APIRouter(prefix="/beta-access", tags=["beta-access"])


class BetaAccessReviewTokenPayload(BaseModel):
    token: str
    decision: str


class BetaAccessStatusUpdate(BaseModel):
    status: str


def _serialize_request(request: models.BetaAccessRequest) -> dict:
    return {
        "id": str(request.id),
        "email": request.email,
        "status": request.status,
        "requested_at": request.requested_at.isoformat() if request.requested_at else None,
        "reviewed_at": request.reviewed_at.isoformat() if request.reviewed_at else None,
        "reviewer_email": request.reviewer_email,
    }


def _serialize_user(user: models.User, request: Optional[models.BetaAccessRequest]) -> dict:
    return {
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "beta_access_status": user.beta_access_status,
        "last_request": _serialize_request(request) if request else None,
    }


@router.post("/request", status_code=status.HTTP_201_CREATED)
def request_beta_access(
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    # Resolve email from headers locally to avoid module-level dependency import issues
    from core.api.auth import resolve_identity_from_headers, get_or_create_user
    # Respect DEV_MODE: only default to dev@localhost when DEV_MODE == "true"
    try:
        is_dev_mode = dev_mode_active()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DEV_MODE misconfigured") from exc
    if is_dev_mode:
        user_email = "dev@localhost"
        display_name = "Development User"
    else:
        display_name, user_email = resolve_identity_from_headers(
            x_auth_request_user=x_auth_request_user,
            x_auth_request_email=x_auth_request_email,
            x_forwarded_user=x_forwarded_user,
            x_forwarded_email=x_forwarded_email,
        )

    if not user_email:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_record = db.query(models.User).filter(models.User.email == user_email).first()
    if not user_record:
        try:
            user_record = get_or_create_user(db, email=user_email, display_name=display_name or user_email.split('@')[0])
        except Exception:
            user_record = None

    service = BetaAccessService(db)
    result = service.request_beta_access(user_id=user_record.id if user_record else None, email=user_email)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.post("/review/{request_id}", status_code=status.HTTP_200_OK)
def review_beta_access_request(
    request_id: uuid.UUID,
    decision: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    user_context = Depends(require_beta_access_admin),
):
    user, current_user = user_context
    service = BetaAccessService(db)
    result = service.review_beta_access_request(request_id, decision, user.email, reason, user.id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.post("/review/{request_id}/token", status_code=status.HTTP_200_OK)
def review_beta_access_request_with_token(
    request_id: uuid.UUID,
    payload: BetaAccessReviewTokenPayload,
    db: Session = Depends(get_db),
):
    service = BetaAccessService(db)
    result = service.review_beta_access_request_with_token(request_id, payload.token, payload.decision)
    if not result['success']:
        detail = result.get('message', 'Failed to review request via token.')
        status_code = 410 if 'expired' in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail)
    return result


@router.get("/status")
def get_beta_access_status(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    service = BetaAccessService(db)
    status = service.get_beta_access_status(user.id)
    # Include latest request (if any) for transparency
    from core.db.repositories import beta_access as beta_repo
    latest = beta_repo.get_beta_access_request_by_email(db, user.email)
    return {
        "status": status,
        "last_request": _serialize_request(latest) if latest else None,
    }


@router.get("/pending")
def get_pending_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_context = Depends(require_beta_access_admin),
):
    user, current_user = user_context
    service = BetaAccessService(db)
    requests = service.get_pending_requests(skip, limit)
    return {"requests": requests}


@router.get("/pending/stuck")
def get_stuck_pending_requests(
    older_than_days: int = 7,
    db: Session = Depends(get_db),
    user_context = Depends(require_beta_access_admin),
):
    """
    List pending requests older than the provided threshold (days).
    """
    user, current_user = user_context
    from datetime import datetime, timezone, timedelta
    threshold = datetime.now(timezone.utc) - timedelta(days=max(1, older_than_days))
    from core.db import models
    q = db.query(models.BetaAccessRequest).filter(
        models.BetaAccessRequest.status == 'pending',
        models.BetaAccessRequest.requested_at < threshold
    ).order_by(models.BetaAccessRequest.requested_at.asc())
    rows = q.all()
    return {"requests": [_serialize_request(r) for r in rows], "older_than_days": older_than_days}


@router.post("/review/{request_id}/resend-token", status_code=status.HTTP_200_OK)
def resend_review_token(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(require_beta_access_admin),
):
    """
    Re-send the review token email to admins for a specific pending request.
    """
    user, current_user = user_context
    request = beta_repo.get_beta_access_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Request already {request.status}")
    service = BetaAccessService(db)
    # Reuse existing helper that emails admins
    service._send_admin_notification_email(request.id, request.email, request.review_token)
    return {"success": True}


@router.get("/admin/users", status_code=status.HTTP_200_OK)
def list_beta_access_users(
    db: Session = Depends(get_db),
    user_context = Depends(require_beta_access_admin),
):
    user, current_user = user_context
    users = db.query(models.User).order_by(models.User.email).all()
    requests = db.query(models.BetaAccessRequest).all()

    latest_by_email = {}
    for req in requests:
        key = req.email.lower()
        existing = latest_by_email.get(key)
        existing_ts = existing.requested_at if existing and existing.requested_at else datetime.min
        candidate_ts = req.requested_at if req.requested_at else datetime.min
        if existing is None or candidate_ts >= existing_ts:
            latest_by_email[key] = req

    data = [_serialize_user(u, latest_by_email.get(u.email.lower())) for u in users]
    return {"users": data}


@router.patch("/admin/users/{user_id}", status_code=status.HTTP_200_OK)
def update_beta_access_user_status(
    user_id: uuid.UUID,
    payload: BetaAccessStatusUpdate,
    db: Session = Depends(get_db),
    user_context = Depends(require_beta_access_admin),
):
    admin_user, current_user = user_context
    desired = (payload.status or "").strip().lower()
    allowed_statuses = {"accepted", "denied", "revoked", "not_requested"}
    if desired not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid beta access status provided.")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    previous_status = user.beta_access_status
    if previous_status == desired:
        return {"success": True, "user": _serialize_user(user, beta_repo.get_beta_access_request_by_email(db, user.email))}

    user.beta_access_status = desired

    request = beta_repo.get_beta_access_request_by_email(db, user.email)
    reviewer_email = admin_user.email

    if desired in {"accepted", "denied"} and request:
        beta_repo.update_beta_access_request_status(
            db,
            request.id,
            desired,
            reviewer_email,
            "Manual status update via beta access admin console",
        )
        request = beta_repo.get_beta_access_request_by_email(db, user.email)
    elif desired in {"revoked", "not_requested"} and request and request.status != 'denied':
        beta_repo.update_beta_access_request_status(
            db,
            request.id,
            'denied',
            reviewer_email,
            "Access manually revoked via beta access admin console",
        )
        request = beta_repo.get_beta_access_request_by_email(db, user.email)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to persist beta access status update.") from exc
    db.refresh(user)

    audit_log(
        db,
        action=AuditAction.BETA_ACCESS_REVIEW,
        status=AuditStatus.SUCCESS,
        target_type='beta_access_user',
        target_id=user.id,
        actor_user_id=admin_user.id,
        metadata={
            "manual": True,
            "previous_status": previous_status,
            "new_status": desired,
        },
    )

    return {"success": True, "user": _serialize_user(user, request)}
