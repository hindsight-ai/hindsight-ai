"""
Consolidation suggestion repository functions.

Implements CRUD for ConsolidationSuggestion records plus the
``apply_consolidation`` business transaction (creates a merged MemoryBlock,
archives originals, and attaches keywords — all in one DB transaction).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import cast, exists, func, select
from sqlalchemy.orm import Session

from core.db import models, schemas, scope_utils
from core.utils.scopes import SCOPE_PERSONAL, SCOPE_ORGANIZATION


class ConsolidationOriginalMismatchError(ValueError):
    """Raised when a consolidation suggestion's originals do not share the
    same (visibility_scope, owner_user_id, organization_id) tuple. Mixed
    originals previously caused the new merged block to be minted under
    `original_memory_ids[0].owner_user_id`, regardless of who validated."""


def _get_or_create_keyword(
    db: Session,
    keyword_text: str,
    *,
    visibility_scope: str = SCOPE_PERSONAL,
    owner_user_id=None,
    organization_id=None,
):
    """Get or create a keyword by text and scope.

    Private helper used by apply_consolidation. The similar
    ``_get_or_create_keyword_scoped`` in repositories/memory_blocks.py
    is used for memory block creation; this one is kept here to avoid
    importing a private from a repository.
    """
    processed_keyword_text = keyword_text.strip().rstrip('.')

    q = db.query(models.Keyword).filter(
        models.Keyword.keyword_text == processed_keyword_text,
        models.Keyword.visibility_scope == visibility_scope,
    )
    if visibility_scope == SCOPE_ORGANIZATION and organization_id is not None:
        q = q.filter(models.Keyword.organization_id == organization_id)
    elif visibility_scope == SCOPE_PERSONAL and owner_user_id is not None:
        q = q.filter(models.Keyword.owner_user_id == owner_user_id)
    keyword = q.first()
    if not keyword:
        keyword = models.Keyword(
            keyword_text=processed_keyword_text,
            visibility_scope=visibility_scope,
            owner_user_id=owner_user_id,
            organization_id=organization_id,
        )
        db.add(keyword)
        db.flush()
    return keyword


def create_consolidation_suggestion(db: Session, suggestion: schemas.ConsolidationSuggestionCreate):
    db_suggestion = models.ConsolidationSuggestion(
        group_id=suggestion.group_id,
        suggested_content=suggestion.suggested_content,
        suggested_lessons_learned=suggestion.suggested_lessons_learned,
        suggested_keywords=suggestion.suggested_keywords,
        original_memory_ids=suggestion.original_memory_ids,
        status=suggestion.status or 'pending'
    )
    db.add(db_suggestion)
    db.commit()
    db.refresh(db_suggestion)
    return db_suggestion


def get_consolidation_suggestion(db: Session, suggestion_id: uuid.UUID):
    return db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()


def get_consolidation_suggestions(db: Session, status: Optional[str] = None, group_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.ConsolidationSuggestion)
    if status:
        query = query.filter(models.ConsolidationSuggestion.status == status)
    if group_id:
        query = query.filter(models.ConsolidationSuggestion.group_id == group_id)

    total_items = query.count()
    suggestions = query.offset(skip).limit(limit).all()

    return suggestions, total_items


def get_consolidation_suggestions_scoped(
    db: Session,
    *,
    status: Optional[str] = None,
    group_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
    current_user: Optional[dict] = None,
):
    """List consolidation suggestions with SQL-level scope narrowing via EXISTS.

    This reduces cross-scope noise by ensuring at least one original memory
    matches the active scope. Membership checks (can_read) should still be
    enforced by callers at the API layer.
    """
    mb = models.MemoryBlock
    filters = []
    scope = getattr(scope_ctx, 'scope', None) if scope_ctx else None
    if scope == 'organization' and getattr(scope_ctx, 'organization_id', None):
        filters.append(mb.organization_id == scope_ctx.organization_id)
        filters.append(mb.visibility_scope == 'organization')
    elif scope == 'personal' and current_user and current_user.id:
        filters.append(mb.owner_user_id == current_user.id)
        filters.append(mb.visibility_scope == 'personal')
    elif scope == 'public':
        filters.append(mb.visibility_scope == 'public')

    exists_cond = exists(
        select(1).
        where(
            mb.id.in_(
                select(cast(func.jsonb_array_elements_text(models.ConsolidationSuggestion.original_memory_ids), mb.id.type))
            ),
            *filters
        )
    )

    query = db.query(models.ConsolidationSuggestion).filter(exists_cond)
    if status:
        query = query.filter(models.ConsolidationSuggestion.status == status)
    if group_id:
        query = query.filter(models.ConsolidationSuggestion.group_id == group_id)
    total_items = query.count()
    suggestions = query.offset(skip).limit(limit).all()
    return suggestions, total_items


def update_consolidation_suggestion(db: Session, suggestion_id: uuid.UUID, suggestion: schemas.ConsolidationSuggestionUpdate):
    db_suggestion = db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()
    if db_suggestion:
        update_data = suggestion.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_suggestion, key, value)
        db.commit()
        db.refresh(db_suggestion)
    return db_suggestion


def delete_consolidation_suggestion(db: Session, suggestion_id: uuid.UUID):
    db_suggestion = db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()
    if db_suggestion:
        db.delete(db_suggestion)
        db.commit()
        return True
    return False


def apply_consolidation(db: Session, suggestion_id: uuid.UUID):
    db_suggestion = db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()
    if db_suggestion and db_suggestion.status == 'pending':
        original_memory_ids = db_suggestion.original_memory_ids
        if original_memory_ids:
            norm_ids = []
            for mid in original_memory_ids:
                if isinstance(mid, uuid.UUID):
                    norm_ids.append(mid)
                else:
                    try:
                        norm_ids.append(uuid.UUID(str(mid)))
                    except Exception:
                        continue
            if not norm_ids:
                return None
            originals = (
                db.query(models.MemoryBlock)
                .filter(models.MemoryBlock.id.in_(norm_ids))
                .all()
            )
            if not originals:
                return None
            scope_keys = {
                (
                    getattr(o, 'visibility_scope', None),
                    getattr(o, 'owner_user_id', None),
                    getattr(o, 'organization_id', None),
                )
                for o in originals
            }
            if len(scope_keys) > 1:
                raise ConsolidationOriginalMismatchError(
                    f"Consolidation suggestion {suggestion_id} bundles memory blocks "
                    f"with different (scope, owner, org) tuples: {scope_keys}."
                )
            first_memory_block = next(
                (o for o in originals if o.id == norm_ids[0]),
                originals[0],
            )
            if first_memory_block:
                new_memory_block = models.MemoryBlock(
                    agent_id=first_memory_block.agent_id,
                    conversation_id=first_memory_block.conversation_id,
                    content=db_suggestion.suggested_content,
                    lessons_learned=db_suggestion.suggested_lessons_learned,
                    metadata_col={"consolidated_from": [str(i) for i in norm_ids]},
                    visibility_scope=getattr(first_memory_block, 'visibility_scope', 'personal'),
                    owner_user_id=getattr(first_memory_block, 'owner_user_id', None),
                    organization_id=getattr(first_memory_block, 'organization_id', None),
                )
                db.add(new_memory_block)
                db.flush()

                for keyword_text in db_suggestion.suggested_keywords or []:
                    keyword = _get_or_create_keyword(
                        db,
                        keyword_text,
                        visibility_scope=new_memory_block.visibility_scope,
                        owner_user_id=new_memory_block.owner_user_id,
                        organization_id=new_memory_block.organization_id,
                    )
                    db_mbk = models.MemoryBlockKeyword(memory_id=new_memory_block.id, keyword_id=keyword.keyword_id)
                    db.add(db_mbk)

                for memory_id in norm_ids:
                    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
                    if db_memory_block:
                        db_memory_block.archived = True
                        db_memory_block.archived_at = datetime.now(timezone.utc)
                        db.add(db_memory_block)

                db_suggestion.status = 'validated'
                db.commit()
                db.refresh(new_memory_block)
                return new_memory_block
    return None
