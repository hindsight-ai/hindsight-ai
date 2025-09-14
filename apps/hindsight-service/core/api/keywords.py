"""
Keywords API endpoints.

Create, update, delete, and associate keywords with memory blocks with
scope-aware access control.
"""
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from core.db import schemas, crud, models
from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user
from core.api.permissions import can_read, can_write
from core.utils.scopes import (
    SCOPE_PUBLIC,
    SCOPE_ORGANIZATION,
    SCOPE_PERSONAL,
)
from core.api.deps import (
    get_current_user_context,
    get_current_user_context_or_pat,
    ensure_pat_allows_write,
    ensure_pat_allows_read,
    get_scoped_user_and_context,
)

router = APIRouter(prefix="/keywords", tags=["keywords"])  # normalized prefix

@router.post("/", response_model=schemas.Keyword, status_code=status.HTTP_201_CREATED)
def create_keyword_endpoint(
    keyword: schemas.KeywordCreate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    u, current_user = user_context
    _scope_in = (keyword.visibility_scope or SCOPE_PERSONAL)
    scope = getattr(_scope_in, 'value', _scope_in)
    org_id = getattr(keyword, 'organization_id', None)
    if scope == SCOPE_ORGANIZATION:
        by_org = current_user.get('memberships_by_org', {})
        key = str(org_id) if org_id else None
        m = by_org.get(key) if key else None
        role = (m or {}).get('role') if m else None
        can_write_flag = bool((m or {}).get('can_write'))
        if not m or not (can_write_flag or role in ('owner', 'admin', 'editor')):
            raise HTTPException(status_code=403, detail="No write permission in target organization")
    if scope == SCOPE_PUBLIC and not current_user.get('is_superadmin'):
        raise HTTPException(status_code=403, detail="Only superadmin can create public keywords")
    existing = crud.get_scoped_keyword_by_text(
        db,
        keyword_text=keyword.keyword_text,
        visibility_scope=scope,
        owner_user_id=u.id if scope == SCOPE_PERSONAL else None,
        organization_id=org_id if scope == SCOPE_ORGANIZATION else None,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Keyword already exists in this scope")
    kw_for_create = keyword.model_copy(update={
        'owner_user_id': u.id if scope == SCOPE_PERSONAL else getattr(keyword, 'owner_user_id', None),
    })
    # PAT scope enforcement
    ensure_pat_allows_write(current_user, org_id if scope == SCOPE_ORGANIZATION else None)
    created = crud.create_keyword(db=db, keyword=kw_for_create)
    try:
        from core.audit import log_keyword, AuditAction, AuditStatus
        log_keyword(
            db,
            actor_user_id=u.id,
            organization_id=created.organization_id,
            keyword_id=created.keyword_id,
            action=AuditAction.KEYWORD_CREATE,
            text=created.keyword_text,
            extra_metadata={
                "scope": created.visibility_scope,
                "organization_id": str(created.organization_id) if created.organization_id else None,
            },
            status=AuditStatus.SUCCESS,
        )
    except Exception:
        pass
    return created

@router.get("/", response_model=List[schemas.Keyword])
def get_all_keywords_endpoint(
    skip: int = 0,
    limit: int = 100,
    scope: Optional[str] = None,  # kept for backward-compat; unused with scope_ctx
    organization_id: Optional[uuid.UUID] = None,  # for legacy callers
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    user, current_user, scope_ctx = scoped
    ensure_pat_allows_read(current_user, scope_ctx.organization_id)
    keywords = crud.get_keywords(
        db,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope_ctx=scope_ctx,
    )
    return keywords

@router.get("/{keyword_id}", response_model=schemas.Keyword)
def get_keyword_endpoint(
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    user, current_user, scope_ctx = scoped
    ensure_pat_allows_read(current_user, getattr(db_keyword, 'organization_id', None))
    if not can_read(db_keyword, current_user):
        raise HTTPException(status_code=404, detail="Keyword not found")
    return db_keyword

@router.put("/{keyword_id}", response_model=schemas.Keyword)
def update_keyword_endpoint(
    keyword_id: uuid.UUID,
    keyword: schemas.KeywordUpdate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    existing = crud.get_keyword(db, keyword_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")
    u, current_user = user_context
    ensure_pat_allows_write(current_user, getattr(existing, 'organization_id', None))
    if not can_write(existing, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    db_keyword = crud.update_keyword(db, keyword_id=keyword_id, keyword=keyword)
    try:
        from core.audit import log_keyword, AuditAction, AuditStatus
        log_keyword(
            db,
            actor_user_id=current_user.get('id') if current_user else existing.owner_user_id,
            organization_id=db_keyword.organization_id,
            keyword_id=db_keyword.keyword_id,
            action=AuditAction.KEYWORD_UPDATE,
            text=db_keyword.keyword_text,
            extra_metadata={
                "scope": db_keyword.visibility_scope,
                "organization_id": str(db_keyword.organization_id) if db_keyword.organization_id else None,
            },
            status=AuditStatus.SUCCESS,
        )
    except Exception:
        pass
    return db_keyword

@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_endpoint(
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    existing = crud.get_keyword(db, keyword_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")
    u, current_user = user_context
    ensure_pat_allows_write(current_user, getattr(existing, 'organization_id', None))
    if not can_write(existing, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    success = crud.delete_keyword(db, keyword_id=keyword_id)
    if success:
        try:
            from core.audit import log_keyword, AuditAction, AuditStatus
            log_keyword(
                db,
                actor_user_id=current_user.get('id') if current_user else existing.owner_user_id,
                organization_id=existing.organization_id,
                keyword_id=existing.keyword_id,
                action=AuditAction.KEYWORD_DELETE,
                text=existing.keyword_text,
                extra_metadata={
                    "scope": existing.visibility_scope,
                    "organization_id": str(existing.organization_id) if existing.organization_id else None,
                },
                status=AuditStatus.SUCCESS,
            )
        except Exception:
            pass
    return {"message": "Keyword deleted successfully"}

@router.get("/{keyword_id}/memory-blocks/", response_model=List[schemas.MemoryBlock])
def get_keyword_memory_blocks_endpoint(
    keyword_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Get all memory blocks associated with a specific keyword.
    This endpoint is used for keyword analytics to show which memory blocks use each keyword.
    """
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    user, current_user, scope_ctx = scoped
    ensure_pat_allows_read(current_user, getattr(db_keyword, 'organization_id', None))
    if not can_read(db_keyword, current_user):
        raise HTTPException(status_code=404, detail="Keyword not found")
    memory_blocks = crud.get_keyword_memory_blocks(
        db,
        keyword_id=keyword_id,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope_ctx=scope_ctx,
    )
    return memory_blocks

@router.get("/{keyword_id}/memory-blocks/count")
def get_keyword_memory_blocks_count_endpoint(
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Get the count of memory blocks associated with a specific keyword.
    This endpoint is used for displaying usage statistics on keyword cards.
    """
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    user, current_user, scope_ctx = scoped
    ensure_pat_allows_read(current_user, getattr(db_keyword, 'organization_id', None))
    if not can_read(db_keyword, current_user):
        raise HTTPException(status_code=404, detail="Keyword not found")
    count = crud.get_keyword_memory_blocks_count(
        db,
        keyword_id=keyword_id,
        current_user=current_user,
        scope_ctx=scope_ctx,
    )
    return {"count": count}
