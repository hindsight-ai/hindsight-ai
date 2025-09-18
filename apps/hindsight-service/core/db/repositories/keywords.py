"""
Keyword repository functions.

Implements keyword CRUD and associations, including scoped lookups and
scope-aware list queries.
"""
from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.db import models, schemas, scope_utils
from core.utils.scopes import SCOPE_PERSONAL, SCOPE_ORGANIZATION


def create_keyword(db: Session, keyword: schemas.KeywordCreate):
    db_keyword = models.Keyword(
        keyword_text=keyword.keyword_text,
        visibility_scope=getattr(keyword, 'visibility_scope', SCOPE_PERSONAL) or SCOPE_PERSONAL,
        owner_user_id=getattr(keyword, 'owner_user_id', None),
        organization_id=getattr(keyword, 'organization_id', None),
    )
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword


def get_keyword(db: Session, keyword_id: uuid.UUID):
    return db.query(models.Keyword).filter(models.Keyword.keyword_id == keyword_id).first()


def get_keyword_by_text(db: Session, keyword_text: str):
    return db.query(models.Keyword).filter(models.Keyword.keyword_text == keyword_text).first()


def get_scoped_keyword_by_text(
    db: Session,
    keyword_text: str,
    *,
    visibility_scope: str,
    owner_user_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    def _coerce_uuid(val):
        if val is None:
            return None
        if isinstance(val, uuid.UUID):
            return val
        try:
            return uuid.UUID(str(val))
        except Exception:
            return None

    owner_uuid = _coerce_uuid(owner_user_id)
    org_uuid = _coerce_uuid(organization_id)

    q = db.query(models.Keyword).filter(
        models.Keyword.visibility_scope == visibility_scope,
        func.lower(models.Keyword.keyword_text) == func.lower(keyword_text),
    )
    if visibility_scope == SCOPE_ORGANIZATION and org_uuid is not None:
        q = q.filter(models.Keyword.organization_id == org_uuid)
    elif visibility_scope == SCOPE_PERSONAL and owner_uuid is not None:
        q = q.filter(models.Keyword.owner_user_id == owner_uuid)
    return q.first()


def get_keywords(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    q = db.query(models.Keyword)
    q = scope_utils.apply_scope_filter(q, current_user, models.Keyword)
    if scope_ctx is not None:
        q = scope_utils.apply_optional_scope_narrowing(q, scope_ctx.scope, scope_ctx.organization_id, models.Keyword)
    else:
        q = scope_utils.apply_optional_scope_narrowing(q, scope, organization_id, models.Keyword)
    return q.offset(skip).limit(limit).all()


def update_keyword(db: Session, keyword_id: uuid.UUID, keyword: schemas.KeywordUpdate):
    db_keyword = db.query(models.Keyword).filter(models.Keyword.keyword_id == keyword_id).first()
    if db_keyword:
        for key, value in keyword.model_dump(exclude_unset=True).items():
            setattr(db_keyword, key, value)
        db.commit()
        db.refresh(db_keyword)
    return db_keyword


def delete_keyword(db: Session, keyword_id: uuid.UUID):
    if keyword_id is None:
        return None
    try:
        db_keyword = db.query(models.Keyword).filter(
            models.Keyword.keyword_id == keyword_id
        ).first()
        if db_keyword:
            db.delete(db_keyword)
            db.commit()
        return db_keyword
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to delete keyword {keyword_id}: {str(e)}")


def create_memory_block_keyword(db: Session, memory_id: uuid.UUID, keyword_id: uuid.UUID):
    db_mbk = models.MemoryBlockKeyword(memory_id=memory_id, keyword_id=keyword_id)
    db.add(db_mbk)
    db.commit()
    db.refresh(db_mbk)
    return db_mbk


def delete_memory_block_keyword(db: Session, memory_id: uuid.UUID, keyword_id: uuid.UUID):
    db_mbk = db.query(models.MemoryBlockKeyword).filter(
        models.MemoryBlockKeyword.memory_id == memory_id,
        models.MemoryBlockKeyword.keyword_id == keyword_id,
    ).first()
    if db_mbk:
        db.delete(db_mbk)
        db.commit()
    return db_mbk


def get_memory_block_keywords(db: Session, memory_id: uuid.UUID) -> List[schemas.Keyword]:
    return (
        db.query(models.Keyword)
        .join(models.MemoryBlockKeyword)
        .filter(models.MemoryBlockKeyword.memory_id == memory_id)
        .all()
    )


def get_keyword_memory_blocks(
    db: Session,
    keyword_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
):
    q = (
        db.query(models.MemoryBlock)
        .join(models.MemoryBlockKeyword)
        .filter(models.MemoryBlockKeyword.keyword_id == keyword_id)
    )
    q = scope_utils.apply_scope_filter(q, current_user, models.MemoryBlock)
    if scope_ctx is not None:
        q = scope_utils.apply_optional_scope_narrowing(q, scope_ctx.scope, scope_ctx.organization_id, models.MemoryBlock)
    return q.offset(skip).limit(limit).all()


def get_keyword_memory_blocks_count(
    db: Session,
    keyword_id: uuid.UUID,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
) -> int:
    q = (
        db.query(models.MemoryBlock)
        .join(models.MemoryBlockKeyword)
        .filter(models.MemoryBlockKeyword.keyword_id == keyword_id)
    )
    q = scope_utils.apply_scope_filter(q, current_user, models.MemoryBlock)
    if scope_ctx is not None:
        q = scope_utils.apply_optional_scope_narrowing(q, scope_ctx.scope, scope_ctx.organization_id, models.MemoryBlock)
    return q.count()
