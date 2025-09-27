"""
FastAPI app assembly: middleware and router wiring.
Includes selected endpoints that span multiple resource modules.
"""
import logging
import os
from fastapi import FastAPI, Header, Depends, HTTPException, status, APIRouter, Body
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
import math

# Configure logging
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
logger.info("app_startup: log_level=%s", LOG_LEVEL_NAME)



from core.db import models, schemas, crud
from core.db.database import engine, get_db
from core.pruning.pruning_service import get_pruning_service
from core.pruning.compression_service import get_compression_service
from core.api.auth import (
    resolve_identity_from_headers,
    get_or_create_user,
    get_user_memberships,
    is_beta_access_admin,
)
from core.api.deps import (
    get_current_user_context,
    get_current_user_context_or_pat,
    ensure_pat_allows_write,
    ensure_pat_allows_read,
    get_scoped_user_and_context,
)
from core.api.orgs import router as orgs_router
from core.api.agents import router as agents_router
from core.api.keywords import router as keywords_router
from core.api.memory_blocks import router as memory_blocks_router
from core.api.audits import router as audits_router
from core.api.bulk_operations import router as bulk_operations_router
from core.api.notifications import router as notifications_router
from core.api.consolidation import router as consolidation_router
from core.api.support import router as support_router
from core.api.users import router as users_router
from core.api.beta_access import router as beta_access_router
from core.api.permissions import can_read, can_write, can_manage_org
from core.utils.scopes import (
    ALL_SCOPES,
    SCOPE_PUBLIC,
    SCOPE_ORGANIZATION,
    SCOPE_PERSONAL,
)
from core.services.search_service import SearchService
from core.utils.runtime import dev_mode_active
from core.utils.feature_flags import get_feature_flags, llm_features_enabled

# Database schema is managed by Alembic migrations.

app = FastAPI(
    title="Intelligent AI Agent Memory Service",
    description="API for managing AI agent memories, including creation, retrieval, and feedback.",
    version="1.0.0",
)

# Avoid implicit trailing-slash redirects for predictable URLs
try:
    app.router.redirect_slashes = False
except Exception:
    pass

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "https://app.hindsight-ai.com",
    "https://app-staging.hindsight-ai.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware: enforce read-only for unauthenticated requests
@app.middleware("http")
async def enforce_readonly_for_guests(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # In dev mode, allow; authentication is handled by route dependencies
        import os
        is_dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

        if not is_dev_mode:
            try:
                path = request.url.path or ""
            except Exception:
                path = ""
            if path.startswith("/beta-access/review/") and path.endswith("/token"):
                return await call_next(request)
            h = request.headers
            user_present = (
                h.get("x-auth-request-user")
                or h.get("x-auth-request-email")
                or h.get("x-forwarded-user")
                or h.get("x-forwarded-email")
            )
            # Allow Personal Access Tokens to pass; route dependencies validate
            pat_present = h.get("authorization") or h.get("x-api-key")
            if not user_present and not pat_present:
                return JSONResponse(
                    {"detail": "Guest mode is read-only. Sign in to perform changes."},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
    return await call_next(request)

# Middleware: require explicit scope metadata on write operations for scoped resources
@app.middleware("http")
async def enforce_write_scope_metadata(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        try:
            path = request.url.path or ""
        except Exception:
            path = ""
        # Only enforce for scope-managed resources
        if (
            path.startswith("/agents")
            or path.startswith("/keywords")
            or path.startswith("/memory-blocks")
            or path.startswith("/consolidation")
            or path.startswith("/consolidation-suggestions/")
        ):
            h = request.headers
            # When a PAT is supplied (Authorization bearer token or X-API-Key),
            # downstream dependencies already enforce scope/organization semantics
            # based on the token itself. In that case we skip the header guard here
            # so PAT consumers do not have to echo redundant scope metadata.
            pat_present = bool(h.get("Authorization") or h.get("X-API-Key"))
            if not pat_present:
                qp = request.query_params
                scope_val = (h.get("X-Active-Scope") or qp.get("scope") or "").strip().lower()
                if not scope_val:
                    return JSONResponse({"detail": "scope_required"}, status_code=status.HTTP_400_BAD_REQUEST)
                if scope_val == "organization":
                    org_id = (h.get("X-Organization-Id") or qp.get("organization_id") or "").strip()
                    if not org_id:
                        return JSONResponse({"detail": "organization_id_required"}, status_code=status.HTTP_400_BAD_REQUEST)
    return await call_next(request)

router = APIRouter()



@router.post("/memory-blocks/{memory_id}/change-scope", response_model=schemas.MemoryBlock)
def change_memory_block_scope(
    memory_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context_or_pat),
):
    mb = crud.get_memory_block(db, memory_id)
    if not mb:
        raise HTTPException(status_code=404, detail="Memory block not found")
    u, current_user = user_context

    target_scope = (payload.get("visibility_scope") or '').lower()
    if target_scope not in ALL_SCOPES:
        raise HTTPException(status_code=422, detail="Invalid target visibility_scope")

    target_org_id = payload.get("organization_id")
    new_owner_user_id = payload.get("new_owner_user_id")

    # Permission to move
    from core.api.permissions import can_move_scope
    if target_scope == SCOPE_ORGANIZATION:
        if not target_org_id:
            raise HTTPException(status_code=422, detail="organization_id required for organization scope")
        try:
            target_org_uuid = uuid.UUID(str(target_org_id))
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid organization_id")
        # PAT org restriction (if applicable)
        ensure_pat_allows_write(current_user, target_org_uuid)
        # Consent check: moving personal -> organization requires owner consent unless superadmin
        if mb.visibility_scope == SCOPE_PERSONAL and not (current_user.get('is_superadmin') or mb.owner_user_id == current_user.get('id')):
            raise HTTPException(status_code=409, detail="Owner consent required to move personal data to organization")
        if not can_move_scope(mb, SCOPE_ORGANIZATION, target_org_uuid, current_user):
            raise HTTPException(status_code=403, detail="Forbidden")
    elif target_scope == SCOPE_PERSONAL:
        if not can_move_scope(mb, SCOPE_PERSONAL, None, current_user):
            # Superadmin override allowed
            if not current_user.get("is_superadmin"):
                raise HTTPException(status_code=403, detail="Forbidden")
    elif target_scope == SCOPE_PUBLIC:
        if not current_user.get("is_superadmin"):
            raise HTTPException(status_code=403, detail="Only superadmin can publish to public")

    # Determine new ownership fields (capture previous state first)
    previous_scope = mb.visibility_scope
    previous_org_id = mb.organization_id
    previous_owner_id = mb.owner_user_id
    if target_scope == SCOPE_ORGANIZATION:
        mb.visibility_scope = SCOPE_ORGANIZATION
        mb.organization_id = target_org_uuid
        mb.owner_user_id = None
    elif target_scope == SCOPE_PERSONAL:
        owner_id = u.id
        if new_owner_user_id:
            try:
                owner_uuid = uuid.UUID(str(new_owner_user_id))
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid new_owner_user_id")
            if not current_user.get("is_superadmin"):
                raise HTTPException(status_code=403, detail="Only superadmin can set a different personal owner")
            owner_id = owner_uuid
        mb.visibility_scope = SCOPE_PERSONAL
        mb.owner_user_id = owner_id
        mb.organization_id = None
    else:  # public
        if not current_user.get("is_superadmin"):
            raise HTTPException(status_code=403, detail="Only superadmin can publish to public")
        mb.visibility_scope = SCOPE_PUBLIC
        mb.organization_id = None
        mb.owner_user_id = None

    db.commit()
    db.refresh(mb)
    # Audit log
    try:
        from core.audit import log, AuditAction, AuditStatus
        log(
            db,
            action=AuditAction.MEMORY_SCOPE_CHANGE,
            status=AuditStatus.SUCCESS,
            target_type="memory_block",
            target_id=mb.id,
            actor_user_id=current_user.get("id"),
            organization_id=mb.organization_id or previous_org_id,
            metadata={
                "old_scope": previous_scope,
                "new_scope": mb.visibility_scope,
                "old_org_id": str(previous_org_id) if previous_org_id else None,
                "new_org_id": str(mb.organization_id) if mb.organization_id else None,
                "old_owner_user_id": str(previous_owner_id) if previous_owner_id else None,
                "new_owner_user_id": str(mb.owner_user_id) if mb.owner_user_id else None,
            },
        )
    except Exception:
        pass
    return mb
    # Re-query keywords since relationship may not be loaded
    current_keywords = mb.keywords
    new_keyword_ids = []
    for kw in current_keywords:
        target_kw = crud._get_or_create_keyword(
            db,
            kw.keyword_text,
            visibility_scope=mb.visibility_scope,
            owner_user_id=mb.owner_user_id,
            organization_id=mb.organization_id,
        )
        new_keyword_ids.append(target_kw.keyword_id)

    # Update associations to point to target-scope keywords
    # Delete existing associations and recreate to the new keyword ids
    db.query(models.MemoryBlockKeyword).filter(models.MemoryBlockKeyword.memory_id == mb.id).delete(synchronize_session=False)
    for kid in new_keyword_ids:
        db.add(models.MemoryBlockKeyword(memory_id=mb.id, keyword_id=kid))

    db.commit()
    db.refresh(mb)
    return mb

# Consolidation Trigger Endpoint
# Consolidation endpoints moved to core.api.consolidation

"""Support and build-info endpoints moved to core.api.support"""

@router.get("/user-info")
def get_user_info(
    request: Request,
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """
    Return authenticated user info and memberships.
    - Dev mode (DEV_MODE=true): returns a stable dev user and ensures it exists.
    - Normal mode: reads headers set by oauth2-proxy, upserts user, and returns memberships.
    """
    try:
        is_dev_mode = dev_mode_active()
    except RuntimeError as exc:
        logger.error("DEV_MODE misconfiguration detected: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DEV_MODE misconfigured")

    flags = get_feature_flags()

    if is_dev_mode:
        email = "dev@localhost"
        user = get_or_create_user(db, email=email, display_name="Development User")
        if getattr(user, "beta_access_status", "") != "accepted":
            user.beta_access_status = "accepted"
            try:
                db.commit()
            except Exception:
                db.rollback()
            else:
                db.refresh(user)

        # Comment out automatic superadmin privileges for dev user to test non-superadmin functionality
        # if not user.is_superadmin:
        #     user.is_superadmin = True
        #     db.commit()
        #     db.refresh(user)
            
        memberships = get_user_memberships(db, user.id)
        beta_admin = is_beta_access_admin(user.email) or bool(user.is_superadmin)
        return {
            "authenticated": True,
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "is_superadmin": bool(user.is_superadmin),
            "beta_access_status": user.beta_access_status,
            "memberships": memberships,
            "beta_access_admin": beta_admin,
            "llm_features_enabled": flags["llm_features_enabled"],
        }

    # If a PAT is provided, authenticate via PAT first
    if authorization or x_api_key:
        try:
            from core.api.deps import get_current_user_context_or_pat
            user, current_user = get_current_user_context_or_pat(
                db=db,
                authorization=authorization,
                x_api_key=x_api_key,
                x_auth_request_user=x_auth_request_user,
                x_auth_request_email=x_auth_request_email,
                x_forwarded_user=x_forwarded_user,
                x_forwarded_email=x_forwarded_email,
            )
            memberships = current_user.get("memberships") or []
            return {
                "authenticated": True,
                "user_id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "is_superadmin": bool(getattr(user, "is_superadmin", False)),
                "beta_access_status": user.beta_access_status,
                "memberships": memberships,
                "pat": current_user.get("pat") or None,
                "llm_features_enabled": flags["llm_features_enabled"],
            }
        except HTTPException as e:
            return JSONResponse({"authenticated": False, "detail": e.detail}, status_code=e.status_code)

    # Local dev fallback (no oauth, no PAT) when running on localhost
    try:
        allow_local = os.getenv("ALLOW_LOCAL_DEV_AUTH", "true").lower() == "true"
    except Exception:
        allow_local = True
    host = (request.headers.get('host') or '').lower()
    client_ip = None
    try:
        client_ip = request.client.host if request.client else None
    except Exception:
        client_ip = None
    is_local = allow_local and (host.startswith('localhost') or host.startswith('127.0.0.1') or client_ip in ('127.0.0.1', '::1', None))
    if is_local and not any([x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email]):
        email = os.getenv('DEV_LOCAL_EMAIL', 'dev@localhost')
        name = os.getenv('DEV_LOCAL_NAME', 'Development User')
        user = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, user.id)
        return {
            "authenticated": True,
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "is_superadmin": bool(user.is_superadmin),
            "beta_access_status": user.beta_access_status,
            "memberships": memberships,
            "llm_features_enabled": flags["llm_features_enabled"],
        }

    # Otherwise, fallback to oauth2-proxy headers
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if not name and not email:
        return JSONResponse({"authenticated": False}, status_code=status.HTTP_401_UNAUTHORIZED)

    if not email:
        return {"authenticated": True, "user": name or None, "email": None}

    user = get_or_create_user(db, email=email, display_name=name)
    memberships = get_user_memberships(db, user.id)
    beta_admin = is_beta_access_admin(user.email) or bool(user.is_superadmin)
    return {
        "authenticated": True,
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_superadmin": bool(user.is_superadmin),
        "beta_access_status": user.beta_access_status,
        "memberships": memberships,
        "beta_access_admin": beta_admin,
        "llm_features_enabled": flags["llm_features_enabled"],
    }

# Dashboard Stats Endpoints
@router.get("/conversations/count")
def get_conversations_count_endpoint(
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Get the count of unique conversations from memory blocks.
    This endpoint is used by the dashboard to display conversation statistics.
    """
    try:
        user, current_user, scope_ctx = scoped
        ensure_pat_allows_read(current_user, scope_ctx.organization_id)
        count = crud.get_unique_conversation_count(db, current_user=current_user, scope_ctx=scope_ctx)
        return {"count": count or 0}  # Return 0 if count is None
    except Exception as e:
        logger.error(f"Error getting conversations count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting conversations count: {str(e)}")

# Pruning Endpoints
@router.post("/memory/prune/suggest", response_model=dict)
def generate_pruning_suggestions_endpoint(
    request: dict = None,
    db: Session = Depends(get_db)
):
    """
    Generate memory block pruning suggestions using LLM evaluation.
    Returns a batch of memory blocks with pruning scores for human review.
    """
    if request is None:
        request = {}

    if not llm_features_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM features are currently disabled")
    
    batch_size = request.get("batch_size", 50)
    target_count = request.get("target_count")
    max_iterations = request.get("max_iterations", 10)
    
    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Fallback scoring will be used.")
    
    try:
        # Get pruning service instance
        pruning_service = get_pruning_service(llm_api_key)
        
        # Generate pruning suggestions
        suggestions = pruning_service.generate_pruning_suggestions(
            db=db,
            batch_size=batch_size,
            target_count=target_count,
            max_iterations=max_iterations
        )
        
        return suggestions
    except Exception as e:
        logger.error(f"Error generating pruning suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating pruning suggestions: {str(e)}")

@router.post("/memory/prune/confirm", response_model=dict)
def confirm_pruning_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Confirm and archive selected memory blocks for pruning.
    This endpoint archives the memory blocks that were approved for pruning.
    """
    memory_block_ids = request.get("memory_block_ids", [])
    
    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided for pruning")
    
    archived_count = 0
    failed_count = 0
    failed_blocks = []
    
    try:
        for memory_id_str in memory_block_ids:
            try:
                memory_id = uuid.UUID(memory_id_str)
                success = crud.archive_memory_block(db, memory_id=memory_id)
                if success:
                    archived_count += 1
                    logger.info(f"Successfully archived memory block {memory_id_str} for pruning")
                else:
                    failed_count += 1
                    failed_blocks.append(memory_id_str)
                    logger.warning(f"Failed to archive memory block {memory_id_str}")
            except ValueError:
                failed_count += 1
                failed_blocks.append(memory_id_str)
                logger.error(f"Invalid UUID format for memory block ID: {memory_id_str}")
            except Exception as e:
                failed_count += 1
                failed_blocks.append(memory_id_str)
                logger.error(f"Error archiving memory block {memory_id_str}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"Pruning confirmation processed successfully",
            "archived_count": archived_count,
            "failed_count": failed_count,
            "failed_blocks": failed_blocks if failed_blocks else None
        }
    except Exception as e:
        logger.error(f"Error confirming pruning: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error confirming pruning: {str(e)}")

# Compression Endpoints
@router.post("/memory-blocks/{memory_id}/compress", response_model=dict)
def compress_memory_block_endpoint(
    memory_id: uuid.UUID,
    request: dict = None,
    db: Session = Depends(get_db)
):
    """
    Compress a memory block using LLM to create a more condensed version.
    Returns the compression suggestion for user review and approval.
    """
    if request is None:
        request = {}

    if not llm_features_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM features are currently disabled")

    user_instructions = request.get("user_instructions", "")

    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Cannot perform compression.")
        raise HTTPException(status_code=500, detail="LLM service not available for compression")

    try:
        # Get compression service instance
        compression_service = get_compression_service(llm_api_key)

        # Compress the memory block
        compression_result = compression_service.compress_memory_block(
            db=db,
            memory_id=memory_id,
            user_instructions=user_instructions
        )

        # Check if compression was successful
        if "error" in compression_result:
            raise HTTPException(
                status_code=400 if "not found" in compression_result["message"].lower() else 500,
                detail=compression_result["message"]
            )

        return compression_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error compressing memory block {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error compressing memory block: {str(e)}")

@router.post("/memory-blocks/{memory_id}/compress/apply", response_model=schemas.MemoryBlock)
def apply_memory_compression_endpoint(
    memory_id: uuid.UUID,
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Apply the compressed version to replace the original memory block content.
    """
    compressed_content = request.get("compressed_content")
    compressed_lessons = request.get("compressed_lessons_learned")

    if not compressed_content:
        raise HTTPException(status_code=400, detail="Compressed content is required")

    try:
        # Update the memory block with compressed content
        update_data = schemas.MemoryBlockUpdate(
            content=compressed_content,
            lessons_learned=compressed_lessons
        )

        updated_memory = crud.update_memory_block(
            db=db,
            memory_id=memory_id,
            memory_block=update_data
        )

        if not updated_memory:
            raise HTTPException(status_code=404, detail="Memory block not found")

        logger.info(f"Successfully applied compression to memory block {memory_id}")
        return updated_memory

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying compression to memory block {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error applying compression: {str(e)}")

# Bulk Keyword Generation Endpoint
@router.post("/memory-blocks/bulk-generate-keywords", response_model=dict)
def bulk_generate_keywords_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Generate keywords for multiple memory blocks using basic keyword extraction.
    Returns suggested keywords for each memory block for user review and approval.
    """
    memory_block_ids = request.get("memory_block_ids", [])
    
    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided")
    
    try:
        suggestions = []
        successful_count = 0
        failed_count = 0
        
        for memory_id_str in memory_block_ids:
            try:
                memory_id = uuid.UUID(memory_id_str)
                memory_block = crud.get_memory_block(db, memory_id=memory_id)
                
                if not memory_block:
                    logger.warning(f"Memory block not found: {memory_id_str}")
                    continue
                
                # Extract keywords from content and lessons_learned
                content_text = (memory_block.content or '') + ' ' + (memory_block.lessons_learned or '')
                
                # Simple keyword extraction (enhanced version of the disabled function)
                suggested_keywords = extract_keywords_enhanced(content_text)
                
                if suggested_keywords:
                    suggestions.append({
                        "memory_block_id": str(memory_id),
                        "memory_block_content_preview": (memory_block.content or '')[:100] + "..." if len(memory_block.content or '') > 100 else (memory_block.content or ''),
                        "suggested_keywords": suggested_keywords,
                        "current_keywords": [kw.keyword_text for kw in memory_block.keywords] if memory_block.keywords else []
                    })
                    successful_count += 1
                else:
                    logger.info(f"No keywords could be extracted for memory block {memory_id_str}")
                    failed_count += 1
                    
            except ValueError:
                failed_count += 1
                logger.error(f"Invalid UUID format: {memory_id_str}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing memory block {memory_id_str}: {str(e)}")
        
        return {
            "suggestions": suggestions,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "total_processed": len(memory_block_ids),
            "message": f"Generated keyword suggestions for {successful_count} memory blocks"
        }
        
    except Exception as e:
        logger.error(f"Error in bulk keyword generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating keywords: {str(e)}")

def extract_keywords_enhanced(text: str) -> List[str]:
    """
    Enhanced keyword extraction using simple text analysis.
    This is a fallback function when spaCy is not available.
    """
    if not text or not text.strip():
        return []
    
    import re
    from collections import Counter
    
    # Clean and normalize text
    text = text.lower()
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
        'his', 'hers', 'its', 'our', 'their', 'myself', 'yourself', 'himself', 'herself', 'itself',
        'ourselves', 'yourselves', 'themselves', 'what', 'which', 'who', 'whom', 'whose', 'where',
        'when', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'now', 'here', 'there', 'then', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
        'further', 'once', 'during', 'before', 'after', 'above', 'below', 'between', 'through',
        'into', 'from', 'about', 'against', 'within', 'without'
    }
    
    # Extract words (alphanumeric sequences of 3+ characters)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    
    # Filter out stop words and get word frequencies
    meaningful_words = [word for word in words if word not in stop_words]
    word_freq = Counter(meaningful_words)
    
    # Look for technical terms, proper nouns (capitalized words in original text), and domain-specific keywords
    technical_patterns = [
        r'\b(?:api|database|server|client|service|system|process|function|method|class|object|data|model|algorithm|framework|library|module|component|interface|protocol|network|security|authentication|authorization|token|session|cache|memory|storage|disk|cpu|gpu|performance|optimization|configuration|deployment|environment|production|development|testing|debugging|logging|monitoring|analytics|metrics|dashboard|report|analysis|query|search|filter|sort|pagination|validation|error|exception|warning|info|debug|trace)\b',
        r'\b(?:python|javascript|typescript|java|c\+\+|golang|rust|php|ruby|html|css|sql|json|xml|yaml|api|rest|graphql|http|https|tcp|udp|websocket|oauth|jwt|ssl|tls|aws|azure|gcp|docker|kubernetes|git|github|gitlab|jenkins|terraform|ansible|nginx|apache|postgresql|mysql|mongodb|redis|elasticsearch|kafka|rabbitmq|react|vue|angular|node|express|flask|django|fastapi|spring|laravel)\b',
        r'\b(?:user|admin|client|customer|account|profile|settings|preferences|notification|email|password|login|logout|signup|registration|dashboard|home|page|view|screen|form|input|button|menu|navigation|header|footer|sidebar|modal|dialog|popup|tab|accordion|carousel|slider|chart|graph|table|list|grid|card|tile|widget|component)\b'
    ]
    
    # Find technical terms
    technical_words = set()
    for pattern in technical_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        technical_words.update(matches)
    
    # Combine high-frequency words with technical terms
    # Get top words by frequency (minimum frequency of 2 or if text is short, frequency of 1)
    min_freq = 2 if len(meaningful_words) > 20 else 1
    frequent_words = [word for word, count in word_freq.most_common(10) if count >= min_freq]
    
    # Combine and deduplicate
    keywords = list(set(frequent_words + list(technical_words)))
    
    # Sort by relevance (technical terms first, then by frequency)
    def keyword_score(word):
        tech_score = 10 if word.lower() in technical_words else 0
        freq_score = word_freq.get(word, 0)
        return tech_score + freq_score
    
    keywords.sort(key=keyword_score, reverse=True)
    
    # Return top 8 keywords
    return keywords[:8]

@router.post("/memory-blocks/bulk-apply-keywords", response_model=dict)
def bulk_apply_keywords_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Apply selected keywords to memory blocks.
    Expects a list of memory block IDs with their selected keywords.
    """
    applications = request.get("applications", [])
    
    if not applications:
        raise HTTPException(status_code=400, detail="No keyword applications provided")
    
    try:
        successful_count = 0
        failed_count = 0
        results = []
        
        for application in applications:
            memory_block_id = application.get("memory_block_id")
            selected_keywords = application.get("selected_keywords", [])
            
            if not memory_block_id or not selected_keywords:
                failed_count += 1
                continue
                
            try:
                memory_id = uuid.UUID(memory_block_id)
                memory_block = crud.get_memory_block(db, memory_id=memory_id)
                
                if not memory_block:
                    failed_count += 1
                    continue
                
                added_keywords = []
                skipped_keywords = []
                
                for keyword_text in selected_keywords:
                    # Get or create keyword
                    keyword = crud.get_keyword_by_text(db, keyword_text=keyword_text)
                    if not keyword:
                        keyword_create = schemas.KeywordCreate(keyword_text=keyword_text)
                        keyword = crud.create_keyword(db=db, keyword=keyword_create)
                    
                    # Check if association already exists
                    existing_association = db.query(models.MemoryBlockKeyword).filter(
                        models.MemoryBlockKeyword.memory_id == memory_id,
                        models.MemoryBlockKeyword.keyword_id == keyword.keyword_id
                    ).first()
                    
                    if not existing_association:
                        crud.create_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword.keyword_id)
                        added_keywords.append(keyword_text)
                    else:
                        skipped_keywords.append(keyword_text)
                
                results.append({
                    "memory_block_id": memory_block_id,
                    "added_keywords": added_keywords,
                    "skipped_keywords": skipped_keywords,
                    "success": True
                })
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Error applying keywords to memory block {memory_block_id}: {str(e)}")
                results.append({
                    "memory_block_id": memory_block_id,
                    "error": str(e),
                    "success": False
                })
                failed_count += 1
        
        return {
            "results": results,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "message": f"Applied keywords to {successful_count} memory blocks"
        }
        
    except Exception as e:
        logger.error(f"Error in bulk keyword application: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error applying keywords: {str(e)}")

@router.post("/memory-blocks/bulk-compact", response_model=dict)
async def bulk_compact_memory_blocks_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Bulk compact multiple memory blocks using AI compression.
    This endpoint processes multiple memory blocks for compaction with optional concurrency.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    if not llm_features_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM features are currently disabled")

    logger.info(f"Bulk compaction request received with {len(request.get('memory_block_ids', []))} blocks")
    
    memory_block_ids = request.get("memory_block_ids", [])
    user_instructions = request.get("user_instructions", "")
    max_concurrent = request.get("max_concurrent", 1)  # Default to 1 for safety
    
    # Validate max_concurrent parameter
    if not isinstance(max_concurrent, int) or max_concurrent < 1:
        max_concurrent = 1
    if max_concurrent > 10:  # Reasonable upper limit to prevent abuse
        max_concurrent = 10
    
    logger.info(f"Using max_concurrent: {max_concurrent}")
    
    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided")
    
    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Cannot perform bulk compaction.")
        raise HTTPException(status_code=500, detail="LLM service not available for compaction")
    
    logger.info(f"Starting bulk compaction for {len(memory_block_ids)} blocks with {max_concurrent} concurrent processes")
    
    def process_single_block(memory_id_str: str):
        """Process a single memory block in a separate thread."""
        try:
            memory_id = uuid.UUID(memory_id_str)
            logger.info(f"Starting compression for block {memory_id_str}")
            
            # Get compression service instance (in the thread)
            compression_service = get_compression_service(llm_api_key)
            
            # Create a new DB session for this thread
            db_gen = get_db()
            thread_db = next(db_gen)
            
            try:
                # Compress the memory block
                compression_result = compression_service.compress_memory_block(
                    db=thread_db,
                    memory_id=memory_id,
                    user_instructions=user_instructions
                )
                logger.info(f"Compression completed for block {memory_id_str}")
                
                # Check if compression was successful
                if "error" not in compression_result:
                    # Auto-apply the compression if successful
                    compressed_content = compression_result.get("compressed_content")
                    compressed_lessons = compression_result.get("compressed_lessons_learned")
                    
                    if compressed_content:
                        # Update the memory block with compressed content
                        update_data = schemas.MemoryBlockUpdate(
                            content=compressed_content,
                            lessons_learned=compressed_lessons
                        )
                        
                        updated_memory = crud.update_memory_block(
                            db=thread_db,
                            memory_id=memory_id,
                            memory_block=update_data
                        )
                        
                        if updated_memory:
                            return {
                                "memory_block_id": memory_id_str,
                                "success": True,
                                "original_length": len(compression_result.get("original_content", "")),
                                "compressed_length": len(compressed_content),
                                "compression_ratio": compression_result.get("compression_ratio", 0),
                                "message": "Successfully compacted"
                            }
                        else:
                            return {
                                "memory_block_id": memory_id_str,
                                "success": False,
                                "error": "Failed to update memory block"
                            }
                    else:
                        return {
                            "memory_block_id": memory_id_str,
                            "success": False,
                            "error": "No compressed content returned"
                        }
                else:
                    return {
                        "memory_block_id": memory_id_str,
                        "success": False,
                        "error": compression_result.get("message", "Compression failed")
                    }
            finally:
                thread_db.close()
                    
        except ValueError:
            logger.error(f"Invalid UUID format: {memory_id_str}")
            return {
                "memory_block_id": memory_id_str,
                "success": False,
                "error": "Invalid UUID format"
            }
        except Exception as e:
            logger.error(f"Error compacting memory block {memory_id_str}: {str(e)}")
            return {
                "memory_block_id": memory_id_str,
                "success": False,
                "error": str(e)
            }
    
    try:
        # Use ThreadPoolExecutor for concurrent processing
        # Use a fresh event loop retrieval that is future-safe; if no loop set, create one
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop; create a temporary one (mainly for sync test contexts)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Create tasks for all memory blocks
            tasks = [
                loop.run_in_executor(executor, process_single_block, memory_id)
                for memory_id in memory_block_ids
            ]
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        successful_count = 0
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                processed_results.append({
                    "memory_block_id": "unknown",
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
                if result.get("success", False):
                    successful_count += 1
                else:
                    failed_count += 1
        
        return {
            "results": processed_results,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "total_processed": len(memory_block_ids),
            "message": f"Successfully compacted {successful_count} out of {len(memory_block_ids)} memory blocks"
        }
        
    except Exception as e:
        logger.error(f"Error in bulk memory block compaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error compacting memory blocks: {str(e)}")

# Enhanced Search Endpoints

@router.get("/memory-blocks/search/fulltext", response_model=List[schemas.MemoryBlockWithScore])
def search_memory_blocks_fulltext_endpoint(
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    min_score: float = 0.1,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Perform BM25-like full-text search on memory blocks using PostgreSQL's full-text search capabilities.
    
    Args:
        query: Search query string
        agent_id: Optional agent filter
        conversation_id: Optional conversation filter
        limit: Maximum number of results (default: 50)
        min_score: Minimum relevance score threshold (default: 0.1)
        include_archived: Whether to include archived memory blocks (default: False)
    
    Returns:
        List of memory blocks with search scores, ranked by relevance
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        current_user = None
        if authorization or x_api_key:
            try:
                _u, current_user = get_current_user_context_or_pat(
                    db=db,
                    authorization=authorization,
                    x_api_key=x_api_key,
                    x_auth_request_user=x_auth_request_user,
                    x_auth_request_email=x_auth_request_email,
                    x_forwarded_user=x_forwarded_user,
                    x_forwarded_email=x_forwarded_email,
                )
            except HTTPException:
                raise
        else:
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
                    "is_superadmin": bool(u.is_superadmin),
                    "memberships": memberships,
                    "memberships_by_org": {m["organization_id"]: m for m in memberships},
                }

        # Narrow memberships to PAT org if present
        if current_user and current_user.get("pat") and current_user["pat"].get("organization_id"):
            pat_org = str(current_user["pat"]["organization_id"])  # string key
            m = (current_user.get("memberships_by_org") or {}).get(pat_org)
            if m:
                current_user = {
                    **current_user,
                    "memberships": [m],
                    "memberships_by_org": {pat_org: m},
                }

        results, metadata = crud.search_memory_blocks_fulltext(
            db=db,
            query=query.strip(),
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit,
            min_score=min_score,
            include_archived=include_archived,
            current_user=current_user,
        )
        
        logger.info(f"Full-text search for '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.exception("Error in full-text search: %s", e)
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/memory-blocks/search/semantic", response_model=List[schemas.MemoryBlockWithScore])
def search_memory_blocks_semantic_endpoint(
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    similarity_threshold: float = 0.7,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Perform semantic search on memory blocks using stored embeddings."""
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        current_user = None
        if authorization or x_api_key:
            try:
                _u, current_user = get_current_user_context_or_pat(
                    db=db,
                    authorization=authorization,
                    x_api_key=x_api_key,
                    x_auth_request_user=x_auth_request_user,
                    x_auth_request_email=x_auth_request_email,
                    x_forwarded_user=x_forwarded_user,
                    x_forwarded_email=x_forwarded_email,
                )
            except HTTPException:
                raise
        else:
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

        if current_user and current_user.get("pat") and current_user["pat"].get("organization_id"):
            pat_org = str(current_user["pat"]["organization_id"])  # string key
            m = (current_user.get("memberships_by_org") or {}).get(pat_org)
            if m:
                current_user = {
                    **current_user,
                    "memberships": [m],
                    "memberships_by_org": {pat_org: m},
                }
        results, metadata = crud.search_memory_blocks_semantic(
            db=db,
            query=query.strip(),
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit,
            similarity_threshold=similarity_threshold,
            include_archived=include_archived,
            current_user=current_user,
        )
        
        expansion_meta = metadata.get("expansion", {})
        logger.info(
            "Semantic search for '%s' returned %d results (mode=%s, fallback=%s, expansion_applied=%s)",
            query,
            len(results),
            metadata.get("search_type"),
            metadata.get("fallback_reason"),
            expansion_meta.get("expansion_applied"),
        )
        return results
        
    except Exception as e:
        logger.exception("Error in semantic search: %s", e)
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/memory-blocks/search/hybrid", response_model=List[schemas.MemoryBlockWithScore])
def search_memory_blocks_hybrid_endpoint(
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    fulltext_weight: float = 0.7,
    semantic_weight: float = 0.3,
    min_combined_score: float = 0.1,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Perform hybrid search combining full-text and semantic search with weighted scoring.
    
    Args:
        query: Search query string
        agent_id: Optional agent filter
        conversation_id: Optional conversation filter
        limit: Maximum number of results (default: 50)
        fulltext_weight: Weight for full-text search results (default: 0.7)
        semantic_weight: Weight for semantic search results (default: 0.3)
        min_combined_score: Minimum combined score threshold (default: 0.1)
        include_archived: Whether to include archived memory blocks (default: False)
    
    Returns:
        List of memory blocks with combined scores from both search methods
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    # Validate weights
    if abs(fulltext_weight + semantic_weight - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="Fulltext and semantic weights must sum to 1.0")
    
    try:
        current_user = None
        if authorization or x_api_key:
            try:
                _u, current_user = get_current_user_context_or_pat(
                    db=db,
                    authorization=authorization,
                    x_api_key=x_api_key,
                    x_auth_request_user=x_auth_request_user,
                    x_auth_request_email=x_auth_request_email,
                    x_forwarded_user=x_forwarded_user,
                    x_forwarded_email=x_forwarded_email,
                )
            except HTTPException:
                raise
        else:
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
                    "is_superadmin": bool(u.is_superadmin),
                    "memberships": memberships,
                    "memberships_by_org": {m["organization_id"]: m for m in memberships},
                }

        if current_user and current_user.get("pat") and current_user["pat"].get("organization_id"):
            pat_org = str(current_user["pat"]["organization_id"])  # string key
            m = (current_user.get("memberships_by_org") or {}).get(pat_org)
            if m:
                current_user = {
                    **current_user,
                    "memberships": [m],
                    "memberships_by_org": {pat_org: m},
                }
        results, metadata = crud.search_memory_blocks_hybrid(
            db=db,
            query=query.strip(),
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit,
            fulltext_weight=fulltext_weight,
            semantic_weight=semantic_weight,
            min_combined_score=min_combined_score,
            include_archived=include_archived,
            current_user=current_user,
        )
        
        expansion_meta = metadata.get("expansion", {})
        logger.info(
            "Hybrid search for '%s' returned %d results (expansion_applied=%s)",
            query,
            len(results),
            expansion_meta.get("expansion_applied"),
        )
        return results
        
    except Exception as e:
        logger.error(f"Error in hybrid search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# Include the main router
app.include_router(router)
app.include_router(users_router)
app.include_router(orgs_router)
app.include_router(agents_router)
app.include_router(keywords_router)
app.include_router(memory_blocks_router)
app.include_router(audits_router)
app.include_router(bulk_operations_router)
app.include_router(notifications_router)
app.include_router(consolidation_router)
app.include_router(support_router)
app.include_router(beta_access_router)

# Include memory optimization router
try:
    from core.api.memory_optimization import router as memory_optimization_router
    app.include_router(memory_optimization_router, prefix="/memory-optimization", tags=["memory-optimization"])
    logger.info("Memory optimization endpoints loaded successfully")
except ImportError as e:
    logger.warning(f"Could not load memory optimization endpoints: {e}")

# Health check endpoint (duplicate but keeping for compatibility)
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "hindsight-service"}
