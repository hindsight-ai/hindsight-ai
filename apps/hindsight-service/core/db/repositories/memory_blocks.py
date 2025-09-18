"""
Memory block repository functions.

Implements memory block CRUD, search/list, archival, and feedback updates.
"""
from __future__ import annotations

import uuid
from typing import Optional, List, Tuple
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, Text

from core.db import models, schemas, scope_utils
from core.utils.scopes import SCOPE_PERSONAL, SCOPE_ORGANIZATION

logger = logging.getLogger(__name__)


def _get_or_create_keyword_scoped(
    db: Session,
    keyword_text: str,
    *,
    visibility_scope: str = SCOPE_PERSONAL,
    owner_user_id=None,
    organization_id=None,
):
    processed = (keyword_text or "").strip().rstrip('.')
    q = db.query(models.Keyword).filter(
        models.Keyword.keyword_text == processed,
        models.Keyword.visibility_scope == visibility_scope,
    )
    if visibility_scope == SCOPE_ORGANIZATION and organization_id is not None:
        q = q.filter(models.Keyword.organization_id == organization_id)
    elif visibility_scope == SCOPE_PERSONAL and owner_user_id is not None:
        q = q.filter(models.Keyword.owner_user_id == owner_user_id)
    kw = q.first()
    if not kw:
        kw = models.Keyword(
            keyword_text=processed,
            visibility_scope=visibility_scope,
            owner_user_id=owner_user_id,
            organization_id=organization_id,
        )
        db.add(kw)
        db.flush()
    return kw


def create_memory_block(db: Session, memory_block: schemas.MemoryBlockCreate):
    db_memory_block = models.MemoryBlock(
        agent_id=memory_block.agent_id,
        conversation_id=memory_block.conversation_id,
        content=memory_block.content,
        errors=memory_block.errors,
        lessons_learned=memory_block.lessons_learned,
        metadata_col=memory_block.metadata_col,
        feedback_score=memory_block.feedback_score or 0,
        visibility_scope=getattr(memory_block, 'visibility_scope', SCOPE_PERSONAL) or SCOPE_PERSONAL,
        owner_user_id=getattr(memory_block, 'owner_user_id', None),
        organization_id=getattr(memory_block, 'organization_id', None),
    )
    db.add(db_memory_block)
    db.flush()

    # Basic keyword extraction using lightweight heuristic extractor
    try:
        from core.utils.keywords import simple_extract_keywords
        tokens = simple_extract_keywords(memory_block.content)
    except Exception:
        tokens = []
    extracted_keywords = set(tokens)

    for keyword_text in extracted_keywords:
        keyword = _get_or_create_keyword_scoped(
            db,
            keyword_text,
            visibility_scope=db_memory_block.visibility_scope,
            owner_user_id=db_memory_block.owner_user_id,
            organization_id=db_memory_block.organization_id,
        )
        db.add(models.MemoryBlockKeyword(memory_id=db_memory_block.id, keyword_id=keyword.keyword_id))

    # Initial neutral feedback
    db.add(
        models.FeedbackLog(
            memory_id=db_memory_block.id,
            feedback_type='neutral',
            feedback_details='Initial memory creation',
        )
    )

    db.commit()
    db.refresh(db_memory_block)
    return schemas.MemoryBlock.model_validate(db_memory_block, from_attributes=True)


def get_memory_block(db: Session, memory_id: uuid.UUID):
    return db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()


def get_all_memory_blocks(
    db: Session,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    search_query: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_feedback_score: Optional[int] = None,
    max_feedback_score: Optional[int] = None,
    min_retrieval_count: Optional[int] = None,
    max_retrieval_count: Optional[int] = None,
    keyword_ids: Optional[List[uuid.UUID]] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 100,
    get_total: bool = False,
    include_archived: bool = False,
    is_archived: Optional[bool] = None,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
    filter_scope: Optional[str] = None,
    filter_organization_id: Optional[uuid.UUID] = None,
) -> List[schemas.MemoryBlock] | Tuple[List[schemas.MemoryBlock], int]:
    query = db.query(models.MemoryBlock).options(
        joinedload(models.MemoryBlock.memory_block_keywords).joinedload(models.MemoryBlockKeyword.keyword)
    )

    query = scope_utils.apply_scope_filter(query, current_user, models.MemoryBlock)

    if is_archived is not None:
        query = query.filter(models.MemoryBlock.archived == is_archived)
    elif not include_archived:
        query = query.filter(models.MemoryBlock.archived == False)

    if agent_id:
        query = query.filter(models.MemoryBlock.agent_id == agent_id)
    if conversation_id:
        query = query.filter(models.MemoryBlock.conversation_id == conversation_id)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                models.MemoryBlock.id.cast(Text).ilike(pattern),
                models.MemoryBlock.content.ilike(pattern),
                models.MemoryBlock.errors.ilike(pattern),
                models.MemoryBlock.lessons_learned.ilike(pattern),
                models.MemoryBlock.metadata_col.cast(Text).ilike(pattern),
                models.MemoryBlock.agent_id.cast(Text).ilike(pattern),
                models.MemoryBlock.conversation_id.cast(Text).ilike(pattern),
            )
        )

    if start_date:
        query = query.filter(models.MemoryBlock.created_at >= start_date)
    if end_date:
        query = query.filter(models.MemoryBlock.created_at <= end_date)

    if min_feedback_score is not None:
        query = query.filter(models.MemoryBlock.feedback_score >= min_feedback_score)
    if max_feedback_score is not None:
        query = query.filter(models.MemoryBlock.feedback_score <= max_feedback_score)

    if min_retrieval_count is not None:
        query = query.filter(models.MemoryBlock.retrieval_count >= min_retrieval_count)
    if max_retrieval_count is not None:
        query = query.filter(models.MemoryBlock.retrieval_count <= max_retrieval_count)

    if keyword_ids:
        query = query.join(models.MemoryBlockKeyword).filter(models.MemoryBlockKeyword.keyword_id.in_(keyword_ids))

    if scope_ctx is not None:
        query = scope_utils.apply_optional_scope_narrowing(
            query, scope_ctx.scope, scope_ctx.organization_id, models.MemoryBlock
        )
    else:
        query = scope_utils.apply_optional_scope_narrowing(query, filter_scope, filter_organization_id, models.MemoryBlock)

    total_count = query.count()

    if sort_by:
        if sort_by == "creation_date":
            order_column = models.MemoryBlock.created_at
        elif sort_by == "feedback_score":
            order_column = models.MemoryBlock.feedback_score
        elif sort_by == "retrieval_count":
            order_column = models.MemoryBlock.retrieval_count
        elif sort_by == "id":
            order_column = models.MemoryBlock.id
        else:
            order_column = models.MemoryBlock.created_at
        query = query.order_by(order_column.desc() if sort_order == "desc" else order_column.asc())
    else:
        query = query.order_by(models.MemoryBlock.created_at.desc())

    memories = query.offset(skip).limit(limit).all()
    if get_total:
        return memories, total_count
    return memories


def update_memory_block(db: Session, memory_id: uuid.UUID, memory_block: schemas.MemoryBlockUpdate):
    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
    if db_memory_block:
        update_data = memory_block.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_memory_block, key, value)
        db.commit()
        db.refresh(db_memory_block)
    return db_memory_block


def archive_memory_block(db: Session, memory_id: uuid.UUID):
    logger.info(f"Attempting to archive memory block with ID: {memory_id}")
    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
    if db_memory_block:
        logger.info(f"Memory block {memory_id} found. Setting archived=True and archived_at.")
        db_memory_block.archived = True
        db_memory_block.archived_at = datetime.now(timezone.utc)
        try:
            db.commit()
            db.refresh(db_memory_block)
            logger.info(
                f"Memory block {memory_id} successfully archived at {db_memory_block.archived_at}."
            )
            return db_memory_block
        except Exception as e:
            db.rollback()
            logger.error(f"Error archiving memory block {memory_id}: {e}")
            raise
    logger.warning(f"Memory block with ID: {memory_id} not found for archiving.")
    return None


def delete_memory_block(db: Session, memory_id: uuid.UUID):
    if memory_id is None:
        return False
    try:
        db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
        if db_memory_block:
            db.delete(db_memory_block)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to delete memory block {memory_id}: {str(e)}")


def retrieve_relevant_memories(
    db: Session,
    keywords: List[str],
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 100,
):
    query = db.query(models.MemoryBlock)
    if agent_id:
        query = query.filter(models.MemoryBlock.agent_id == agent_id)
    if conversation_id:
        query = query.filter(models.MemoryBlock.conversation_id == conversation_id)
    filters = []
    for kw in keywords:
        filters.append(models.MemoryBlock.content.ilike(f"%{kw}%"))
        filters.append(models.MemoryBlock.errors.ilike(f"%{kw}%"))
        filters.append(models.MemoryBlock.lessons_learned.ilike(f"%{kw}%"))
    if filters:
        query = query.filter(or_(*filters))
    return query.limit(limit).all()


def create_feedback_log(db: Session, feedback_log: schemas.FeedbackLogCreate):
    db_feedback_log = models.FeedbackLog(
        memory_id=feedback_log.memory_id,
        feedback_type=feedback_log.feedback_type,
        feedback_details=feedback_log.feedback_details,
    )
    db.add(db_feedback_log)
    db.commit()
    db.refresh(db_feedback_log)
    return db_feedback_log


def report_memory_feedback(
    db: Session, memory_id: uuid.UUID, feedback_type: str, feedback_details: Optional[str] = None
):
    create_feedback_log(
        db, schemas.FeedbackLogCreate(memory_id=memory_id, feedback_type=feedback_type, feedback_details=feedback_details)
    )
    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
    if db_memory_block:
        if feedback_type == 'positive':
            db_memory_block.feedback_score += 1
        elif feedback_type == 'negative':
            db_memory_block.feedback_score -= 1
        db.commit()
        db.refresh(db_memory_block)
    return db_memory_block
