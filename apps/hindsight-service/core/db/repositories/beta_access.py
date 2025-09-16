"""
Beta access repository functions.

Implements CRUD for beta access requests.
"""
from __future__ import annotations

import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from core.db import models


def create_beta_access_request(db: Session, user_id: Optional[uuid.UUID], email: str) -> models.BetaAccessRequest:
    db_request = models.BetaAccessRequest(
        user_id=user_id,
        email=email,
        status='pending',
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


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
    return db.query(models.BetaAccessRequest).filter(models.BetaAccessRequest.email == email).first()


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
