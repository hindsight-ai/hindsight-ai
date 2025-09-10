from typing import List, Optional
import uuid, os, math
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.db import schemas, crud, models
from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.api.permissions import can_read, can_write
from core.search.search_service import SearchService

router = APIRouter(tags=["memory-blocks"])  # Preserve existing paths

@router.get("/memory-blocks/", response_model=schemas.PaginatedMemoryBlocks)
def get_all_memory_blocks_endpoint(
    agent_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    search_query: Optional[str] = None,
    search_type: Optional[str] = "basic",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_feedback_score: Optional[str] = None,
    max_feedback_score: Optional[str] = None,
    min_retrieval_count: Optional[str] = None,
    max_retrieval_count: Optional[str] = None,
    keywords: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 50,
    include_archived: Optional[bool] = False,
    min_score: Optional[float] = None,
    similarity_threshold: Optional[float] = None,
    fulltext_weight: Optional[float] = None,
    semantic_weight: Optional[float] = None,
    min_combined_score: Optional[float] = None,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
    scope: Optional[str] = None,
    organization_id: Optional[str] = None,
):
    # (Condensed version of parsing and logic from main.py)
    from datetime import datetime
    processed_agent_id = None
    if agent_id:
        try:
            processed_agent_id = uuid.UUID(agent_id)
        except ValueError:
            if agent_id != "":
                raise HTTPException(status_code=422, detail="Invalid UUID format for agent_id.")
    processed_conversation_id = None
    if conversation_id:
        try:
            processed_conversation_id = uuid.UUID(conversation_id)
        except ValueError:
            if conversation_id != "":
                raise HTTPException(status_code=422, detail="Invalid UUID format for conversation_id.")
    def parse_dt(val):
        if val and val != "":
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid datetime format for {val}.")
        return None
    processed_start_date = parse_dt(start_date)
    processed_end_date = parse_dt(end_date)
    def parse_int(val, field):
        if val:
            try:
                return int(val)
            except ValueError:
                if val != "":
                    raise HTTPException(status_code=422, detail=f"Invalid integer format for {field}.")
        return None
    processed_min_feedback_score = parse_int(min_feedback_score, 'min_feedback_score')
    processed_max_feedback_score = parse_int(max_feedback_score, 'max_feedback_score')
    processed_min_retrieval_count = parse_int(min_retrieval_count, 'min_retrieval_count')
    processed_max_retrieval_count = parse_int(max_retrieval_count, 'max_retrieval_count')
    processed_keyword_ids = None
    if keywords and keywords != "":
        import uuid as _uuid
        try:
            processed_keyword_ids = [_uuid.UUID(kw.strip()) for kw in keywords.split(',') if kw.strip()]
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid UUID format in keywords parameter.")
    search_query = search_query or None
    sort_by = sort_by or None
    sort_order = sort_order or "asc"
    current_user = None
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if search_query and search_type in ["fulltext", "semantic", "hybrid"]:
        search_service = SearchService()
        try:
            if search_type == "fulltext":
                min_score_val = min_score if min_score is not None else 0.1
                results, metadata = search_service.search_memory_blocks_fulltext(
                    db=db,
                    query=search_query,
                    agent_id=processed_agent_id,
                    conversation_id=processed_conversation_id,
                    limit=skip + limit,
                    min_score=min_score_val,
                    include_archived=include_archived or False,
                    current_user=current_user,
                )
            elif search_type == "semantic":
                similarity_threshold_val = similarity_threshold if similarity_threshold is not None else 0.7
                results, metadata = search_service.search_memory_blocks_semantic(
                    db=db,
                    query=search_query,
                    agent_id=processed_agent_id,
                    conversation_id=processed_conversation_id,
                    limit=skip + limit,
                    similarity_threshold=similarity_threshold_val,
                    include_archived=include_archived or False,
                    current_user=current_user,
                )
            else:  # hybrid
                fulltext_weight_val = fulltext_weight if fulltext_weight is not None else 0.7
                semantic_weight_val = semantic_weight if semantic_weight is not None else 0.3
                min_combined_score_val = min_combined_score if min_combined_score is not None else 0.1
                results, metadata = search_service.search_memory_blocks_hybrid(
                    db=db,
                    query=search_query,
                    agent_id=processed_agent_id,
                    conversation_id=processed_conversation_id,
                    limit=skip + limit,
                    fulltext_weight=fulltext_weight_val,
                    semantic_weight=semantic_weight_val,
                    min_combined_score=min_combined_score_val,
                    include_archived=include_archived or False,
                    current_user=current_user,
                )
            paginated_results = results[skip:skip + limit]
            total_items = len(results)
            memories = paginated_results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    else:
        filter_scope = None
        filter_org_uuid = None
        if scope in ("personal", "organization", "public"):
            filter_scope = scope
        if organization_id:
            try:
                filter_org_uuid = uuid.UUID(organization_id)
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid organization_id")
        memories, total_items = crud.get_all_memory_blocks(
            db=db,
            agent_id=processed_agent_id,
            conversation_id=processed_conversation_id,
            search_query=search_query,
            start_date=processed_start_date,
            end_date=processed_end_date,
            min_feedback_score=processed_min_feedback_score,
            max_feedback_score=processed_max_feedback_score,
            min_retrieval_count=processed_min_retrieval_count,
            max_retrieval_count=processed_max_retrieval_count,
            keyword_ids=processed_keyword_ids,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
            get_total=True,
            include_archived=include_archived or False,
            current_user=current_user,
            filter_scope=filter_scope,
            filter_organization_id=filter_org_uuid,
        )
    total_pages = math.ceil(total_items / limit) if limit > 0 else 0
    return {"items": memories, "total_items": total_items, "total_pages": total_pages}

@router.post("/memory-blocks/", response_model=schemas.MemoryBlock, status_code=status.HTTP_201_CREATED)
def create_memory_block_endpoint(
    memory_block: schemas.MemoryBlockCreate,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    agent = crud.get_agent(db, agent_id=memory_block.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")
    u = get_or_create_user(db, email=email, display_name=name)
    memberships = get_user_memberships(db, u.id)
    memberships_by_org = {m["organization_id"]: m for m in memberships}
    scope = memory_block.visibility_scope or 'personal'
    org_id = str(memory_block.organization_id) if getattr(memory_block, 'organization_id', None) else None
    if scope == 'public' and not u.is_superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can create public data")
    if scope == 'organization':
        if not org_id or org_id not in memberships_by_org:
            raise HTTPException(status_code=403, detail="Not a member of target organization")
        m = memberships_by_org[org_id]
        if not (m.get('can_write') or m.get('role') in ('owner','admin','editor')):
            raise HTTPException(status_code=403, detail="No write permission in target organization")
    mb = memory_block.model_copy(update={
        'visibility_scope': scope,
        'owner_user_id': u.id if scope == 'personal' else None,
        'organization_id': memory_block.organization_id if scope == 'organization' else None,
    })
    db_memory_block = crud.create_memory_block(db=db, memory_block=mb)
    return db_memory_block

@router.get("/memory-blocks/{memory_id}", response_model=schemas.MemoryBlock)
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

@router.put("/memory-blocks/{memory_id}", response_model=schemas.MemoryBlock)
def update_memory_block_endpoint(
    memory_id: uuid.UUID,
    memory_block: schemas.MemoryBlockUpdate,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
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
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    updated = crud.update_memory_block(db, memory_id=memory_id, memory_block=memory_block)
    return updated

@router.post("/memory-blocks/{memory_id}/archive", response_model=schemas.MemoryBlock)
def archive_memory_block_endpoint(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
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
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    db_memory_block = crud.archive_memory_block(db, memory_id=memory_id)
    if db_memory_block is None:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@router.delete("/memory-blocks/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_memory_block_endpoint(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
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
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not getattr(current, 'archived', False):
        crud.archive_memory_block(db, memory_id)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@router.delete("/memory-blocks/{memory_id}/hard-delete", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_memory_block_endpoint(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    current = crud.get_memory_block(db, memory_id)
    if not current:
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
    if not can_write(current, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    success = crud.delete_memory_block(db, memory_id=memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return {"message": "Memory block hard deleted successfully"}

@router.post("/memory-blocks/{memory_id}/feedback/", response_model=schemas.MemoryBlock)
def report_memory_feedback_endpoint(
    memory_id: uuid.UUID,
    feedback: schemas.FeedbackLogCreate,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    if feedback.memory_id != memory_id:
        raise HTTPException(status_code=400, detail="Memory ID mismatch")
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
    if not can_write(db_memory_block, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    updated_memory = crud.report_memory_feedback(
        db=db,
        memory_id=memory_id,
        feedback_type=feedback.feedback_type,
        feedback_details=feedback.feedback_details
    )
    return updated_memory

# Slimmed scope change endpoint omitted for now (kept in main for backwards compat)
