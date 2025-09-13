"""
Memory blocks API endpoints.

CRUD, search, archive, feedback, and related utilities for memory blocks
with comprehensive scope and permission checks.
"""
from typing import List, Optional
import uuid, os, math
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.db import schemas, crud, models
from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.api.permissions import can_read, can_write
from core.utils.scopes import (
    ALL_SCOPES,
    SCOPE_PUBLIC,
    SCOPE_ORGANIZATION,
    SCOPE_PERSONAL,
)
from core.services.search_service import SearchService
from core.api.deps import get_current_user_context, get_current_user_context_or_pat, ensure_pat_allows_write

router = APIRouter(prefix="/memory-blocks", tags=["memory-blocks"])  # normalized prefix

def parse_optional_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    """Convert empty strings to None, otherwise parse as UUID"""
    if not value or value.strip() == "":
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid UUID format: {value}")


@router.post("/", response_model=schemas.MemoryBlock, status_code=status.HTTP_201_CREATED)
def create_memory_block_endpoint(
    memory_block: schemas.MemoryBlockCreate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    agent = crud.get_agent(db, agent_id=memory_block.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    u, current_user = user_context
    memberships_by_org = current_user.get('memberships_by_org', {})
    _scope_in = memory_block.visibility_scope or SCOPE_PERSONAL
    scope = getattr(_scope_in, 'value', _scope_in)
    org_id = str(memory_block.organization_id) if getattr(memory_block, 'organization_id', None) else None
    if scope == SCOPE_PUBLIC and not current_user.get('is_superadmin'):
        raise HTTPException(status_code=403, detail="Only superadmin can create public data")
    if scope == SCOPE_ORGANIZATION:
        if not org_id or org_id not in memberships_by_org:
            raise HTTPException(status_code=403, detail="Not a member of target organization")
        m = memberships_by_org[org_id]
        if not (m.get('can_write') or m.get('role') in ('owner','admin','editor')):
            raise HTTPException(status_code=403, detail="No write permission in target organization")
    # Enforce PAT restrictions for write
    ensure_pat_allows_write(current_user, memory_block.organization_id if scope == SCOPE_ORGANIZATION else None)

    mb = memory_block.model_copy(update={
        'visibility_scope': scope,
        'owner_user_id': u.id if scope == SCOPE_PERSONAL else None,
        'organization_id': memory_block.organization_id if scope == SCOPE_ORGANIZATION else None,
    })
    db_memory_block = crud.create_memory_block(db=db, memory_block=mb)
    return db_memory_block

@router.get("/", response_model=schemas.PaginatedMemoryBlocks)
def get_all_memory_blocks_endpoint(
    skip: int = 0,
    limit: int = 100,
    agent_id: Optional[str] = Query(default=None),
    conversation_id: Optional[str] = Query(default=None),
    search_query: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "desc",
    include_archived: bool = False,
    scope: Optional[str] = None,
    organization_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    # Convert empty string parameters to None to handle frontend behavior
    agent_uuid = parse_optional_uuid(agent_id)
    conversation_uuid = parse_optional_uuid(conversation_id)
    organization_uuid = parse_optional_uuid(organization_id)
    
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }

    # Get total count
    _, total_items = crud.get_all_memory_blocks(
        db,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=0,
        limit=None,
        get_total=True,
        include_archived=include_archived,
        current_user=current_user,
        filter_scope=scope,
        filter_organization_id=organization_uuid,
    )

    # Get paginated results
    memory_blocks = crud.get_all_memory_blocks(
        db,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
        get_total=False,
        include_archived=include_archived,
        current_user=current_user,
        filter_scope=scope,
        filter_organization_id=organization_uuid,
    )

    total_pages = math.ceil(total_items / limit) if limit and limit > 0 else 0

    return {
        "items": memory_blocks,
        "total_items": total_items,
        "total_pages": total_pages
    }

@router.get("/{memory_id}/keywords/", response_model=List[schemas.Keyword])
def get_memory_block_keywords_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")

    keywords = crud.get_memory_block_keywords(db, memory_id=memory_id)
    return keywords

@router.post("/{memory_id}/keywords/{keyword_id}", response_model=schemas.MemoryBlockKeywordAssociation, status_code=status.HTTP_201_CREATED)
def associate_keyword_with_memory_block_endpoint(
    memory_id: uuid.UUID,
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
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
    u, current_user = user_context
    if not can_write(db_memory_block, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    if db_memory_block.visibility_scope != db_keyword.visibility_scope:
        raise HTTPException(status_code=409, detail="Keyword scope mismatch with memory block")
    association = crud.create_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword_id)
    return association

@router.delete("/{memory_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def disassociate_keyword_from_memory_block_endpoint(
    memory_id: uuid.UUID,
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    u, current_user = user_context
    if not can_write(db_memory_block, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    success = crud.delete_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Association not found")
    return {"message": "Association deleted successfully"}

@router.get("/archived/", response_model=schemas.PaginatedMemoryBlocks)
def get_archived_memory_blocks_endpoint(
    skip: int = 0,
    limit: int = 100,
    agent_id: Optional[str] = Query(default=None),
    conversation_id: Optional[str] = Query(default=None),
    search_query: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "desc",
    scope: Optional[str] = None,
    organization_id: Optional[str] = Query(default=None),
    # Additional archived-specific parameters
    feedback_score_range: Optional[str] = None,
    retrieval_count_range: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keywords: Optional[str] = None,
    search_type: Optional[str] = None,
    min_score: Optional[str] = None,
    similarity_threshold: Optional[str] = None,
    fulltext_weight: Optional[str] = None,
    semantic_weight: Optional[str] = None,
    min_combined_score: Optional[str] = None,
    min_feedback_score: Optional[str] = None,
    max_feedback_score: Optional[str] = None,
    min_retrieval_count: Optional[str] = None,
    max_retrieval_count: Optional[str] = None,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    """
    Get archived memory blocks with all the parameters the frontend sends.
    This endpoint specifically filters for archived=true memory blocks.
    """
    # Convert empty string parameters to None to handle frontend behavior
    agent_uuid = parse_optional_uuid(agent_id)
    conversation_uuid = parse_optional_uuid(conversation_id)
    organization_uuid = parse_optional_uuid(organization_id)
    
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }

    # For archived endpoint, we want to show archived blocks more liberally
    # If no specific scope is requested, default to public archived blocks
    effective_scope = scope or SCOPE_PUBLIC
    
    # Get total count of archived items
    _, total_items = crud.get_all_memory_blocks(
        db,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=0,
        limit=None,
        get_total=True,
        is_archived=True,  # Explicitly filter for archived=True only
        current_user=current_user,
        filter_scope=effective_scope,
        filter_organization_id=organization_uuid,
    )

    # Get paginated archived results
    memory_blocks = crud.get_all_memory_blocks(
        db,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
        get_total=False,
        is_archived=True,  # Explicitly filter for archived=True only
        current_user=current_user,
        filter_scope=effective_scope,
        filter_organization_id=organization_uuid,
    )

    total_pages = math.ceil(total_items / limit) if limit and limit > 0 else 0

    return {
        "items": memory_blocks,
        "total_items": total_items,
        "total_pages": total_pages
    }

@router.get("/{memory_id}", response_model=schemas.MemoryBlock)
def get_memory_block_endpoint(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if not can_read(db_memory_block, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    return db_memory_block

@router.put("/{memory_id}", response_model=schemas.MemoryBlock)
def update_memory_block_endpoint(
    memory_id: uuid.UUID,
    memory_block: schemas.MemoryBlockUpdate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
        raise HTTPException(status_code=404, detail="Memory block not found")
    u, current_user = user_context
    # Enforce PAT restrictions (if PAT present and resource is org-scoped)
    ensure_pat_allows_write(current_user, getattr(current, 'organization_id', None))
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    updated = crud.update_memory_block(db, memory_id=memory_id, memory_block=memory_block)
    return updated

@router.post("/{memory_id}/archive", response_model=schemas.MemoryBlock)
def archive_memory_block_endpoint(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
        raise HTTPException(status_code=404, detail="Memory block not found")
    u, current_user = user_context
    ensure_pat_allows_write(current_user, getattr(current, 'organization_id', None))
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    db_memory_block = crud.archive_memory_block(db, memory_id=memory_id)
    if db_memory_block is None:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_memory_block_endpoint(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
        raise HTTPException(status_code=404, detail="Memory block not found")
    u, current_user = user_context
    # PAT restriction enforcement
    ensure_pat_allows_write(current_user, getattr(current, 'organization_id', None))
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not getattr(current, 'archived', False):
        crud.archive_memory_block(db, memory_id)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@router.delete("/{memory_id}/hard-delete", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_memory_block_endpoint(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
        raise HTTPException(status_code=404, detail="Memory block not found")
    u, current_user = user_context
    ensure_pat_allows_write(current_user, getattr(current, 'organization_id', None))
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    success = crud.delete_memory_block(db, memory_id=memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return {"message": "Memory block hard deleted successfully"}

@router.post("/{memory_id}/feedback/", response_model=schemas.MemoryBlock)
def report_memory_feedback_endpoint(
    memory_id: uuid.UUID,
    feedback: schemas.FeedbackLogCreate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    if feedback.memory_id != memory_id:
        raise HTTPException(status_code=400, detail="Memory ID mismatch")
    u, current_user = user_context
    ensure_pat_allows_write(current_user, getattr(db_memory_block, 'organization_id', None))
    if not can_write(db_memory_block, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    updated_memory = crud.report_memory_feedback(
        db=db,
        memory_id=memory_id,
        feedback_type=feedback.feedback_type,
        feedback_details=feedback.feedback_details
    )
    return updated_memory

@router.get("/search/", response_model=List[schemas.MemoryBlock])
def search_memory_blocks_endpoint(
    keywords: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    # This endpoint is for agent-facing semantic search, not for the dashboard's simple search.
    # It will remain as a keyword-based search for now as per the plan,
    # with a note that complex logic will be implemented later.
    keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    if not keyword_list:
        raise HTTPException(status_code=400, detail="At least one keyword is required for search.")
    
    memories = crud.retrieve_relevant_memories(
        db=db,
        keywords=keyword_list,
        agent_id=agent_id,
        conversation_id=conversation_id,
        limit=limit
    )
    return memories

# Slimmed scope change endpoint omitted for now (kept in main for backwards compat)
