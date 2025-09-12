"""
Audit log repository functions.

Implements create and query functions for audit logs.
"""
from __future__ import annotations

import uuid
from typing import Optional
from sqlalchemy.orm import Session

from core.db import schemas, models


def create_audit_log(db: Session, audit_log: schemas.AuditLogCreate, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID] = None):
    data = audit_log.model_dump()
    metadata_payload = data.pop('metadata', None)
    db_audit_log = models.AuditLog(
        **data,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        metadata_json=metadata_payload,
    )
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log


def get_audit_logs(
    db: Session,
    organization_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    action_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.AuditLog)
    if organization_id:
        query = query.filter(models.AuditLog.organization_id == organization_id)
    if user_id:
        query = query.filter(models.AuditLog.actor_user_id == user_id)
    if action_type:
        query = query.filter(models.AuditLog.action_type == action_type)
    if status:
        query = query.filter(models.AuditLog.status == status)
    return query.order_by(models.AuditLog.created_at.desc()).offset(skip).limit(limit).all()

