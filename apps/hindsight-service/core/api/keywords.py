from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from core.db import schemas, crud, models
from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user
from core.api.permissions import can_read, can_write

router = APIRouter(tags=["keywords"])  # Preserve path structure

@router.post("/keywords/", response_model=schemas.Keyword, status_code=status.HTTP_201_CREATED)
def create_keyword_endpoint(
    keyword: schemas.KeywordCreate,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")
    u = get_or_create_user(db, email=email, display_name=name)
    scope = (keyword.visibility_scope or 'personal')
    org_id = getattr(keyword, 'organization_id', None)
    if scope == 'organization':
        # Import at call time so tests can patch core.api.main.get_user_memberships
        from core.api import main as main_module
        memberships = main_module.get_user_memberships(db, u.id)
        by_org = {m['organization_id']: m for m in memberships}
        key = str(org_id) if org_id else None
        m = by_org.get(key) if key else None
        role = (m or {}).get('role') if m else None
        can_write_flag = bool((m or {}).get('can_write'))
        if not m or not (can_write_flag or role in ('owner', 'admin', 'editor')):
            raise HTTPException(status_code=403, detail="No write permission in target organization")
    if scope == 'public' and not u.is_superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can create public keywords")
    existing = crud.get_scoped_keyword_by_text(
        db,
        keyword_text=keyword.keyword_text,
        visibility_scope=scope,
        owner_user_id=u.id if scope == 'personal' else None,
        organization_id=org_id if scope == 'organization' else None,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Keyword already exists in this scope")
    kw_for_create = keyword.model_copy(update={
        'owner_user_id': u.id if scope == 'personal' else getattr(keyword, 'owner_user_id', None),
    })
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
            status=AuditStatus.SUCCESS,
        )
    except Exception:
        pass
    return created

@router.get("/keywords/", response_model=List[schemas.Keyword])
def get_all_keywords_endpoint(
    skip: int = 0,
    limit: int = 100,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        from core.api import main as main_module
        memberships = main_module.get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    keywords = crud.get_keywords(
        db,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope=scope,
        organization_id=organization_id,
    )
    return keywords

@router.get("/keywords/{keyword_id}", response_model=schemas.Keyword)
def get_keyword_endpoint(
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        from core.api import main as main_module
        memberships = main_module.get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if not can_read(db_keyword, current_user):
        raise HTTPException(status_code=404, detail="Keyword not found")
    return db_keyword

@router.put("/keywords/{keyword_id}", response_model=schemas.Keyword)
def update_keyword_endpoint(
    keyword_id: uuid.UUID,
    keyword: schemas.KeywordUpdate,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    existing = crud.get_keyword(db, keyword_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        from core.api import main as main_module
        memberships = main_module.get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if not can_write(existing, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    db_keyword = crud.update_keyword(db, keyword_id=keyword_id, keyword=keyword)
    try:
        from core.audit import log_keyword, AuditAction, AuditStatus
        log_keyword(
            db,
            actor_user_id=u.id if email else current_user.get('id') if current_user else existing.owner_user_id,
            organization_id=db_keyword.organization_id,
            keyword_id=db_keyword.keyword_id,
            action=AuditAction.KEYWORD_UPDATE,
            text=db_keyword.keyword_text,
            status=AuditStatus.SUCCESS,
        )
    except Exception:
        pass
    return db_keyword

@router.delete("/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_endpoint(
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    existing = crud.get_keyword(db, keyword_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        from core.api import main as main_module
        memberships = main_module.get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if not can_write(existing, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    success = crud.delete_keyword(db, keyword_id=keyword_id)
    if success:
        try:
            from core.audit import log_keyword, AuditAction, AuditStatus
            log_keyword(
                db,
                actor_user_id=u.id if email else current_user.get('id') if current_user else existing.owner_user_id,
                organization_id=existing.organization_id,
                keyword_id=existing.keyword_id,
                action=AuditAction.KEYWORD_DELETE,
                text=existing.keyword_text,
                status=AuditStatus.SUCCESS,
            )
        except Exception:
            pass
    return {"message": "Keyword deleted successfully"}

@router.post("/memory-blocks/{memory_id}/keywords/{keyword_id}", response_model=schemas.MemoryBlockKeywordAssociation, status_code=status.HTTP_201_CREATED)
def associate_keyword_with_memory_block_endpoint(
    memory_id: uuid.UUID,
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    existing_association = db.query(models.MemoryBlockKeyword).filter(
        models.MemoryBlockKeyword.memory_id == memory_id,
        models.MemoryBlockKeyword.keyword_id == keyword_id
    ).first()
    if existing_association:
        raise HTTPException(status_code=409, detail="Association already exists")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        from core.api import main as main_module
        memberships = main_module.get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if not can_write(db_memory_block, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    if db_memory_block.visibility_scope != db_keyword.visibility_scope:
        raise HTTPException(status_code=409, detail="Keyword scope mismatch with memory block")
    association = crud.create_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword_id)
    return association

@router.delete("/memory-blocks/{memory_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def disassociate_keyword_from_memory_block_endpoint(
    memory_id: uuid.UUID,
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        from core.api import main as main_module
        memberships = main_module.get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if not can_write(db_memory_block, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    success = crud.delete_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Association not found")
    return {"message": "Association deleted successfully"}

@router.get("/memory-blocks/{memory_id}/keywords/", response_model=List[schemas.Keyword])
def get_memory_block_keywords_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")

    keywords = crud.get_memory_block_keywords(db, memory_id=memory_id)
    return keywords

@router.get("/keywords/{keyword_id}/memory-blocks/", response_model=List[schemas.MemoryBlock])
def get_keyword_memory_blocks_endpoint(keyword_id: uuid.UUID, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    Get all memory blocks associated with a specific keyword.
    This endpoint is used for keyword analytics to show which memory blocks use each keyword.
    """
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    memory_blocks = crud.get_keyword_memory_blocks(db, keyword_id=keyword_id, skip=skip, limit=limit)
    return memory_blocks

@router.get("/keywords/{keyword_id}/memory-blocks/count")
def get_keyword_memory_blocks_count_endpoint(keyword_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Get the count of memory blocks associated with a specific keyword.
    This endpoint is used for displaying usage statistics on keyword cards.
    """
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    count = crud.get_keyword_memory_blocks_count(db, keyword_id=keyword_id)
    return {"count": count}
