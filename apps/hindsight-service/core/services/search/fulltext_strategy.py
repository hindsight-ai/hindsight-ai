"""
Full-text search strategy using PostgreSQL tsvector / ts_rank_cd.
Falls back to BasicSearchStrategy when not on PostgreSQL.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from core.db import models, schemas
from core.services.search.base import SearchStrategy
from core.services.search.scoring import (
    _create_memory_block_with_score,
    _apply_user_scope_filter,
)

if TYPE_CHECKING:
    from core.api.deps import CurrentUserContext

logger = logging.getLogger(__name__)


class FulltextSearchStrategy(SearchStrategy):
    """BM25-like full-text search via PostgreSQL tsvector/tsquery."""

    def __init__(self, basic_strategy: "SearchStrategy"):
        self._basic = basic_strategy

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
        min_score: float = 0.1,
        **kwargs: Any,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """Perform tsvector full-text search; falls back to basic on non-Postgres."""
        start_time = time.time()

        try:
            dialect_name = (
                getattr(db.bind.dialect, "name", "")
                if getattr(db, "bind", None)
                else ""
            )
            if dialect_name != "postgresql":
                fallback_results, meta = self._basic.search(
                    db, query,
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    limit=limit,
                    include_archived=include_archived,
                    current_user=current_user,
                )
                meta.update({
                    "search_type": "fulltext_fallback",
                    "fallback_reason": f"dialect {dialect_name} does not support PostgreSQL full-text",
                })
                return fallback_results, meta

            search_query_func = func.plainto_tsquery("english", query)

            if any(op in query.lower() for op in ["and", "or", "not", '"']):
                search_query_func = func.websearch_to_tsquery("english", query)

            rank_expression = func.ts_rank_cd(
                models.MemoryBlock.search_vector,
                search_query_func,
            )

            base_query = db.query(
                models.MemoryBlock,
                rank_expression.label("rank"),
            ).filter(
                models.MemoryBlock.search_vector.op("@@")(search_query_func)
            ).filter(
                rank_expression >= min_score
            )

            base_query = _apply_user_scope_filter(base_query, current_user, models.MemoryBlock)

            if agent_id:
                base_query = base_query.filter(models.MemoryBlock.agent_id == agent_id)

            if conversation_id:
                base_query = base_query.filter(models.MemoryBlock.conversation_id == conversation_id)

            if not include_archived:
                base_query = base_query.filter(
                    or_(
                        models.MemoryBlock.archived == False,
                        models.MemoryBlock.archived.is_(None),
                    )
                )

            results_with_rank = base_query.order_by(
                rank_expression.desc(),
                models.MemoryBlock.created_at.desc(),
            ).limit(limit).all()

            memory_blocks_with_scores = []
            for memory_block, rank in results_with_rank:
                score = float(rank) if rank else 0.0
                memory_block_with_score = _create_memory_block_with_score(
                    memory_block,
                    score,
                    "fulltext",
                    f"BM25 relevance score: {score:.4f}",
                    {"fulltext_raw": score},
                )
                memory_blocks_with_scores.append(memory_block_with_score)

            search_time = (time.time() - start_time) * 1000

            metadata = {
                "total_search_time_ms": search_time,
                "fulltext_results_count": len(memory_blocks_with_scores),
                "query_terms": query.split(),
                "search_type": "fulltext",
                "min_score_threshold": min_score,
            }

            logger.info(
                "Full-text search for '%s' returned %d results in %.2fms",
                query, len(memory_blocks_with_scores), search_time,
            )

            return memory_blocks_with_scores, metadata

        except Exception as e:
            logger.error("Error in full-text search: %s", str(e))
            raise
