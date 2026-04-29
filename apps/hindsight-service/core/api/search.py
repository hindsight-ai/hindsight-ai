"""
Search API endpoints.

GET /memory-blocks/search/fulltext  — BM25-like full-text search
GET /memory-blocks/search/semantic  — semantic (embedding) search
GET /memory-blocks/search/hybrid    — combined full-text + semantic search
"""
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.db import schemas
from core.db.database import get_db
from core.api.deps import get_scoped_user_and_context, ensure_pat_allows_read
from core.services.search_service import (
    search_memory_blocks_fulltext,
    search_memory_blocks_semantic,
    search_memory_blocks_hybrid,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/memory-blocks/search/fulltext", response_model=List[schemas.MemoryBlockWithScore])
def search_memory_blocks_fulltext_endpoint(
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    min_score: float = 0.1,
    include_archived: bool = False,
    organization_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Perform BM25-like full-text search on memory blocks using PostgreSQL's full-text search capabilities.

    Auth: optional (guests get public-only). PAT scope-narrowing is enforced
    by the unified dep: get_scoped_user_and_context raises 403 on PAT-org
    mismatch and narrows memberships to the PAT's org. ensure_pat_allows_read
    is the explicit defense-in-depth check on the route's organization_id.
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    user, current_user, _scope_ctx = scoped
    if current_user is not None and organization_id:
        ensure_pat_allows_read(current_user, organization_id)

    try:
        results, metadata = search_memory_blocks_fulltext(
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

    except HTTPException:
        raise
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
    organization_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Perform semantic search on memory blocks using stored embeddings.

    Auth: optional. PAT scope-narrowing handled by get_scoped_user_and_context.
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    user, current_user, _scope_ctx = scoped
    if current_user is not None and organization_id:
        ensure_pat_allows_read(current_user, organization_id)

    try:
        results, metadata = search_memory_blocks_semantic(
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

    except HTTPException:
        raise
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
    organization_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Perform hybrid search combining full-text and semantic search with weighted scoring.

    Auth: optional. PAT scope-narrowing handled by get_scoped_user_and_context.
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # Validate weights
    if abs(fulltext_weight + semantic_weight - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="Fulltext and semantic weights must sum to 1.0")

    user, current_user, _scope_ctx = scoped
    if current_user is not None and organization_id:
        ensure_pat_allows_read(current_user, organization_id)

    try:
        results, metadata = search_memory_blocks_hybrid(
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in hybrid search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
