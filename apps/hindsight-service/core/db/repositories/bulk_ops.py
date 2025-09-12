"""
Bulk operations repository functions.

Implements create/read/list/update for bulk operations.
"""
from __future__ import annotations

import uuid
from typing import Optional
from sqlalchemy.orm import Session

from core.db import schemas, models


def create_bulk_operation(db: Session, bulk_operation: schemas.BulkOperationCreate, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID] = None):
    db_bulk_operation = models.BulkOperation(
        **bulk_operation.model_dump(),
        actor_user_id=actor_user_id,
        organization_id=organization_id,
    )
    db.add(db_bulk_operation)
    db.commit()
    db.refresh(db_bulk_operation)
    return db_bulk_operation


def get_bulk_operation(db: Session, bulk_operation_id: uuid.UUID):
    return db.query(models.BulkOperation).filter(models.BulkOperation.id == bulk_operation_id).first()


def get_bulk_operations(db: Session, organization_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.BulkOperation)
    if organization_id:
        query = query.filter(models.BulkOperation.organization_id == organization_id)
    if user_id:
        query = query.filter(models.BulkOperation.actor_user_id == user_id)
    return query.order_by(models.BulkOperation.created_at.desc()).offset(skip).limit(limit).all()


def update_bulk_operation(db: Session, bulk_operation_id: uuid.UUID, bulk_operation: schemas.BulkOperationUpdate):
    db_bulk_operation = db.query(models.BulkOperation).filter(models.BulkOperation.id == bulk_operation_id).first()
    if db_bulk_operation:
        update_data = bulk_operation.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_bulk_operation, key, value)
        db.commit()
        db.refresh(db_bulk_operation)
    return db_bulk_operation

