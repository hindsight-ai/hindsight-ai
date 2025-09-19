"""
Beta access repository functions.

Implements CRUD for beta access requests.
"""
from __future__ import annotations

import uuid
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from core.db import models


def _generate_review_token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


def create_beta_access_request(db: Session, user_id: Optional[uuid.UUID], email: str) -> models.BetaAccessRequest:
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    db_request = models.BetaAccessRequest(
        user_id=user_id,
        email=email,
        status='pending',
        review_token=_generate_review_token(),
        token_expires_at=expires_at,
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


def regenerate_beta_access_review_token(
    db: Session,
    request_id: uuid.UUID,
    lifetime_days: int = 7,
) -> Optional[models.BetaAccessRequest]:
    """
    Generate a fresh review token and extend its expiry for a pending request.

    Returns the updated request or None if not found.
    """
    req = db.query(models.BetaAccessRequest).filter(models.BetaAccessRequest.id == request_id).first()
    if not req:
        return None
    # Only regenerate for pending requests; otherwise tokens should remain cleared
    if (req.status or '').lower() != 'pending':
        return req
    req.review_token = _generate_review_token()
    req.token_expires_at = datetime.now(timezone.utc) + timedelta(days=max(1, lifetime_days))
    db.commit()
    db.refresh(req)
    return req


def get_beta_access_request(db: Session, request_id: uuid.UUID) -> Optional[models.BetaAccessRequest]:
    return db.query(models.BetaAccessRequest).filter(models.BetaAccessRequest.id == request_id).first()


def get_beta_access_requests_by_status(db: Session, status: str, skip: int = 0, limit: int = 100) -> List[models.BetaAccessRequest]:
    return (
        db.query(models.BetaAccessRequest)
        .filter(models.BetaAccessRequest.status == status)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_beta_access_request_by_email(db: Session, email: str) -> Optional[models.BetaAccessRequest]:
    return (
        db.query(models.BetaAccessRequest)
        .filter(models.BetaAccessRequest.email == email)
        .order_by(models.BetaAccessRequest.requested_at.desc())
        .first()
    )


def update_beta_access_request_status(
    db: Session,
    request_id: uuid.UUID,
    status: str,
    reviewer_email: Optional[str] = None,
    decision_reason: Optional[str] = None
) -> Optional[models.BetaAccessRequest]:
    db_request = db.query(models.BetaAccessRequest).filter(models.BetaAccessRequest.id == request_id).first()
    if db_request:
        db_request.status = status
        db_request.reviewed_at = datetime.now()
        db_request.reviewer_email = reviewer_email
        db_request.decision_reason = decision_reason
        db_request.review_token = None
        db_request.token_expires_at = None
        db.commit()
        db.refresh(db_request)
    return db_request


def get_user_beta_access_status(db: Session, user_id: uuid.UUID) -> Optional[str]:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user.beta_access_status if user else None


def update_user_beta_access_status(db: Session, user_id: uuid.UUID, status: str) -> bool:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.beta_access_status = status
        db.commit()
        return True
    return False
