"""
Basic (ILIKE / substring) search strategy — used as fallback for non-Postgres
dialects and for callers that request search_type="basic".
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, String

from core.db import models, schemas
from core.services.search.base import SearchStrategy
from core.services.search.scoring import (
    _create_memory_block_with_score,
    _apply_user_scope_filter,
)

if TYPE_CHECKING:
    from core.api.deps import CurrentUserContext

logger = logging.getLogger(__name__)


class BasicSearchStrategy(SearchStrategy):
    """Fallback full-text search using ILIKE (case-insensitive substring match).

    Works with any SQL dialect — used when PostgreSQL-specific features
    (tsvector, pgvector) are not available.
    """

    def search(
        self,
        db: Session,
        query: str,
        *,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        include_archived: bool = False,
        current_user: Optional["CurrentUserContext"] = None,
        keyword_terms: Optional[List[str]] = None,
        match_any: bool = False,
        **kwargs: Any,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """Perform ILIKE-based substring search across content/errors/lessons fields."""
        start_time = time.time()

        explicit_terms = [term.strip() for term in (keyword_terms or []) if term and term.strip()]
        search_terms = explicit_terms or query.split()
        search_filters = []

        for term in search_terms:
            term_filter = or_(
                models.MemoryBlock.content.ilike(f"%{term}%"),
                models.MemoryBlock.errors.ilike(f"%{term}%"),
                models.MemoryBlock.lessons_learned.ilike(f"%{term}%"),
                models.MemoryBlock.id.cast(String).ilike(f"%{term}%"),
            )
            search_filters.append(term_filter)

        if search_filters:
            combined_filter = or_(*search_filters) if match_any else and_(*search_filters)
        else:
            combined_filter = None

        db_query = db.query(models.MemoryBlock)

        if combined_filter is not None:
            db_query = db_query.filter(combined_filter)

        db_query = _apply_user_scope_filter(db_query, current_user, models.MemoryBlock)

        if agent_id:
            db_query = db_query.filter(models.MemoryBlock.agent_id == agent_id)

        if conversation_id:
            db_query = db_query.filter(models.MemoryBlock.conversation_id == conversation_id)

        if not include_archived:
            db_query = db_query.filter(
                or_(
                    models.MemoryBlock.archived == False,
                    models.MemoryBlock.archived.is_(None),
                )
            )

        raw_results = db_query.order_by(
            models.MemoryBlock.created_at.desc()
        ).limit(limit).all()

        results = []
        for i, memory_block in enumerate(raw_results):
            score = 1.0 - (i / (len(raw_results) + 1))
            result_with_score = _create_memory_block_with_score(
                memory_block,
                score,
                "basic",
                f"Basic search result rank: {i + 1}",
                {"basic_rank": float(i + 1), "basic_score": score},
            )
            results.append(result_with_score)

        search_time = (time.time() - start_time) * 1000

        metadata = {
            "total_search_time_ms": search_time,
            "basic_results_count": len(results),
            "search_type": "basic",
            "search_terms": search_terms,
            "match_any": bool(match_any),
        }

        return results, metadata
