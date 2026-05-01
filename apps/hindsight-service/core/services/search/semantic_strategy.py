"""
Semantic (vector) search strategy using pgvector cosine distance.
Falls back to BasicSearchStrategy when pgvector or embeddings are unavailable.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, Float

from core.db import models, schemas
from core.db.types import HAS_PGVECTOR
from core.services import get_embedding_service
from core.services.search.base import SearchStrategy
from core.services.search.scoring import (
    _create_memory_block_with_score,
    _apply_user_scope_filter,
)

if TYPE_CHECKING:
    from core.api.deps import CurrentUserContext

logger = logging.getLogger(__name__)


class SemanticSearchStrategy(SearchStrategy):
    """Vector similarity search via pgvector cosine distance."""

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
        similarity_threshold: float = 0.7,
        **kwargs: Any,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """Run cosine similarity search; falls back to basic on embedding/pgvector absence."""
        start_time = time.time()

        if not query or not query.strip():
            return [], {
                "total_search_time_ms": 0.0,
                "semantic_results_count": 0,
                "search_type": "semantic",
                "similarity_threshold": similarity_threshold,
                "message": "Empty query",
            }

        embedding_service = get_embedding_service()
        if not embedding_service.is_enabled:
            results, metadata = self._basic.search(
                db, query,
                agent_id=agent_id,
                conversation_id=conversation_id,
                limit=limit,
                include_archived=include_archived,
                current_user=current_user,
            )
            metadata.update({
                "search_type": "semantic_fallback",
                "fallback_reason": "embedding_provider_disabled",
                "similarity_threshold": similarity_threshold,
            })
            return results, metadata

        if not HAS_PGVECTOR:
            results, metadata = self._basic.search(
                db, query,
                agent_id=agent_id,
                conversation_id=conversation_id,
                limit=limit,
                include_archived=include_archived,
                current_user=current_user,
            )
            metadata.update({
                "search_type": "semantic_fallback",
                "fallback_reason": "pgvector_unavailable",
                "similarity_threshold": similarity_threshold,
            })
            return results, metadata

        try:
            raw_embedding = embedding_service.embed_text(query.strip())
            if raw_embedding:
                try:
                    query_embedding = [float(value) for value in raw_embedding]
                except (TypeError, ValueError) as exc:
                    logger.error(
                        "Invalid embedding vector returned for semantic query '%s': %s",
                        query, exc,
                    )
                    query_embedding = None
            else:
                query_embedding = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to embed semantic query '%s': %s", query, exc)
            query_embedding = None

        if not query_embedding:
            results, metadata = self._basic.search(
                db, query,
                agent_id=agent_id,
                conversation_id=conversation_id,
                limit=limit,
                include_archived=include_archived,
                current_user=current_user,
            )
            metadata.update({
                "search_type": "semantic_fallback",
                "fallback_reason": "query_embedding_unavailable",
                "similarity_threshold": similarity_threshold,
            })
            return results, metadata

        dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
        dialect_name = getattr(dialect_name, "name", "") if dialect_name else ""

        if dialect_name != "postgresql":
            results, metadata = self._basic.search(
                db, query,
                agent_id=agent_id,
                conversation_id=conversation_id,
                limit=limit,
                include_archived=include_archived,
                current_user=current_user,
            )
            metadata.update({
                "search_type": "semantic_fallback",
                "fallback_reason": f"dialect_{dialect_name}_unsupported",
                "similarity_threshold": similarity_threshold,
            })
            return results, metadata

        try:
            threshold = float(similarity_threshold)
        except (TypeError, ValueError):
            threshold = 0.7
        threshold = max(min(threshold, 1.0), -1.0)
        max_distance = 1.0 - threshold
        if max_distance < 0:
            max_distance = 0.0

        distance_expr = cast(
            models.MemoryBlock.content_embedding.op("<=>")(query_embedding),
            Float,
        ).label("distance")

        base_query = db.query(models.MemoryBlock, distance_expr).filter(
            models.MemoryBlock.content_embedding.isnot(None)
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

        base_query = (
            base_query.filter(distance_expr <= max_distance)
            .order_by(distance_expr.asc(), models.MemoryBlock.created_at.desc())
            .limit(limit)
        )

        try:
            results_with_similarity = base_query.all()
        except Exception as exc:  # pragma: no cover - defensive database failure
            logger.error("Semantic search query failed: %s", exc)
            fallback_results, metadata = self._basic.search(
                db, query,
                agent_id=agent_id,
                conversation_id=conversation_id,
                limit=limit,
                include_archived=include_archived,
                current_user=current_user,
            )
            metadata.update({
                "search_type": "semantic_fallback",
                "fallback_reason": "semantic_query_error",
                "similarity_threshold": threshold,
            })
            return fallback_results, metadata

        memory_blocks_with_scores: List[schemas.MemoryBlockWithScore] = []
        scores: List[float] = []
        for memory_block, distance in results_with_similarity:
            score = 1.0 - float(distance) if distance is not None else 0.0
            scores.append(score)
            memory_blocks_with_scores.append(
                _create_memory_block_with_score(
                    memory_block,
                    score,
                    "semantic",
                    f"Cosine similarity: {score:.4f}",
                    {
                        "semantic_raw": score,
                        "distance": float(distance) if distance is not None else None,
                    },
                )
            )

        if not memory_blocks_with_scores:
            fallback_results, metadata = self._basic.search(
                db, query,
                agent_id=agent_id,
                conversation_id=conversation_id,
                limit=limit,
                include_archived=include_archived,
                current_user=current_user,
            )
            metadata.update({
                "search_type": "semantic_fallback",
                "fallback_reason": "no_semantic_matches",
                "similarity_threshold": threshold,
            })
            return fallback_results, metadata

        search_time = (time.time() - start_time) * 1000

        metadata = {
            "total_search_time_ms": search_time,
            "semantic_results_count": len(memory_blocks_with_scores),
            "search_type": "semantic",
            "similarity_threshold": threshold,
            "scores": scores,
            "embedding_dimension": len(query_embedding),
        }

        return memory_blocks_with_scores, metadata
