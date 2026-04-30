"""
Search service facade — thin coordinator that delegates to strategy classes.

All public names that callers import from this module are preserved here
either directly or as re-exports from the search sub-package.
"""

import logging
import time  # noqa: F401 — re-exported; tests patch this name on the module
import uuid
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy import cast  # noqa: F401 — re-exported; tests patch on module
from sqlalchemy import func  # noqa: F401 — re-exported; tests patch on module
from sqlalchemy.orm import Session

from core.db import schemas
from core.services import (  # noqa: F401 — re-exported; tests patch these on module
    get_embedding_service,
    get_query_expansion_engine,
)

# Re-exports: config
from core.services.search.config import (  # noqa: F401
    HybridRankingConfig,
    _env_bool,
    _env_float,
    _env_int,
    get_hybrid_ranking_config,
    refresh_hybrid_ranking_config,
)

# Re-exports: shared scoring helpers
from core.services.search.scoring import (  # noqa: F401
    _create_memory_block_with_score,
    _apply_user_scope_filter,
)

# Strategy implementations
from core.services.search.basic_strategy import BasicSearchStrategy
from core.services.search.fulltext_strategy import FulltextSearchStrategy
from core.services.search.semantic_strategy import SemanticSearchStrategy
from core.services.search.hybrid_strategy import HybridSearchStrategy

if TYPE_CHECKING:
    from core.api.deps import CurrentUserContext

logger = logging.getLogger(__name__)


class SearchService:
    """Thin facade that delegates search requests to the appropriate strategy."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        basic = BasicSearchStrategy()
        fulltext = FulltextSearchStrategy(basic_strategy=basic)
        semantic = SemanticSearchStrategy(basic_strategy=basic)
        hybrid = HybridSearchStrategy(
            fulltext_strategy=fulltext,
            semantic_strategy=semantic,
            basic_strategy=basic,
        )
        self._basic = basic
        self._fulltext = fulltext
        self._semantic = semantic
        self._hybrid = hybrid

    def search_memory_blocks_fulltext(
        self,
        db: Session,
        query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        min_score: float = 0.1,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        return self._fulltext.search(
            db, query, agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, min_score=min_score,
            include_archived=include_archived, current_user=current_user,
        )

    def search_memory_blocks_semantic(
        self,
        db: Session,
        query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        similarity_threshold: float = 0.7,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        return self._semantic.search(
            db, query, agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, similarity_threshold=similarity_threshold,
            include_archived=include_archived, current_user=current_user,
        )

    def search_memory_blocks_hybrid(
        self,
        db: Session,
        query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        fulltext_weight: float = 0.7,
        semantic_weight: float = 0.3,
        min_combined_score: float = 0.1,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        return self._hybrid.search(
            db, query, agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, fulltext_weight=fulltext_weight,
            semantic_weight=semantic_weight, min_combined_score=min_combined_score,
            include_archived=include_archived, current_user=current_user,
        )

    def _basic_search_fallback(
        self,
        db: Session,
        search_query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
        *,
        keyword_terms: Optional[List[str]] = None,
        match_any: bool = False,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        return self._basic.search(
            db, search_query, agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, include_archived=include_archived, current_user=current_user,
            keyword_terms=keyword_terms, match_any=match_any,
        )

    def enhanced_search_memory_blocks(
        self,
        db: Session,
        search_query: Optional[str] = None,
        search_type: str = "basic",
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        include_archived: bool = False,
        **search_params,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        if not search_query or search_query.strip() == "":
            return [], {"search_type": search_type, "message": "Empty query"}
        if search_type == "fulltext":
            return self.search_memory_blocks_fulltext(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("min_score", 0.1), include_archived,
            )
        elif search_type == "semantic":
            return self.search_memory_blocks_semantic(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("similarity_threshold", 0.7), include_archived,
            )
        elif search_type == "hybrid":
            return self.search_memory_blocks_hybrid(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("fulltext_weight", 0.7),
                search_params.get("semantic_weight", 0.3),
                search_params.get("min_combined_score", 0.1), include_archived,
            )
        else:
            return self._basic_search_fallback(
                db, search_query, agent_id, conversation_id,
                limit, include_archived, search_params.get("current_user"),
                keyword_terms=search_params.get("keyword_list"),
                match_any=bool(search_params.get("match_any")),
            )

    # Delegation shims for test code that accesses these via SearchService instances
    def _combine_and_rerank_with_scores(self, *args, **kwargs):
        return self._hybrid._combine_and_rerank_with_scores(*args, **kwargs)

    def _combine_and_rerank(self, *args, **kwargs):
        return self._hybrid._combine_and_rerank(*args, **kwargs)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_search_service = None


def get_search_service() -> SearchService:
    """Get or create the global search service instance."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service


# ---------------------------------------------------------------------------
# Module-level search helpers with query-expansion wrappers.
# ---------------------------------------------------------------------------

def _execute_with_query_expansion(
    base_query: str,
    limit: int,
    context: Dict[str, Any],
    runner: Any,
    search_label: str,
) -> Tuple[List["schemas.MemoryBlockWithScore"], Dict[str, Any]]:
    """Run the supplied search callable against the base query and any expansions."""
    expansion_engine = get_query_expansion_engine()
    expansion_result = expansion_engine.expand(base_query, context)

    variants: List[str] = [base_query]
    variants.extend(expansion_result.expanded_queries)

    aggregated: Dict[uuid.UUID, Any] = {}
    variant_runs: List[Dict[str, Any]] = []
    total_time_ms = 0.0
    base_metadata: Optional[Dict[str, Any]] = None

    for variant in variants:
        results, metadata = runner(variant)
        if base_metadata is None:
            base_metadata = dict(metadata)
        variant_runs.append({"query": variant, "results_count": len(results), "metadata": metadata})
        total_time_ms += float(metadata.get("total_search_time_ms", 0.0) or 0.0)
        for item in results:
            existing = aggregated.get(item.id)
            if existing is None or item.search_score > existing.search_score:
                aggregated[item.id] = item

    ordered = sorted(aggregated.values(), key=lambda r: r.search_score, reverse=True)
    limited = ordered[: limit if limit is not None else len(ordered)]

    combined: Dict[str, Any] = base_metadata.copy() if base_metadata else {"search_type": search_label}
    combined["variant_runs"] = variant_runs
    combined["expansion"] = expansion_result.to_metadata()
    combined["combined_results_count"] = len(limited)
    combined["total_search_time_ms"] = total_time_ms

    if expansion_result.expanded_queries:
        combined["search_type"] = f"{combined.get('search_type', search_label)}_expanded"
    else:
        combined.setdefault("search_type", search_label)

    return limited, combined


def search_memory_blocks_fulltext(
    db: Session,
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    min_score: float = 0.1,
    include_archived: bool = False,
    *,
    current_user: Optional[Dict[str, Any]] = None,
) -> Tuple[List["schemas.MemoryBlockWithScore"], Dict[str, Any]]:
    """Full-text search with optional query expansion."""
    svc = get_search_service()
    trimmed = (query or "").strip()
    if not trimmed:
        return [], {"search_type": "fulltext", "message": "Empty query"}

    def _runner(q):
        return svc.search_memory_blocks_fulltext(
            db=db, query=q, agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, min_score=min_score,
            include_archived=include_archived, current_user=current_user,
        )

    return _execute_with_query_expansion(
        trimmed, limit,
        {"search_type": "fulltext",
         "agent_id": str(agent_id) if agent_id else None,
         "conversation_id": str(conversation_id) if conversation_id else None},
        _runner, "fulltext",
    )


def search_memory_blocks_semantic(
    db: Session,
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    similarity_threshold: float = 0.7,
    include_archived: bool = False,
    *,
    current_user: Optional[Dict[str, Any]] = None,
) -> Tuple[List["schemas.MemoryBlockWithScore"], Dict[str, Any]]:
    """Semantic search with optional query expansion."""
    svc = get_search_service()
    trimmed = (query or "").strip()
    if not trimmed:
        return [], {"search_type": "semantic", "message": "Empty query"}

    def _runner(q):
        return svc.search_memory_blocks_semantic(
            db=db, query=q, agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, similarity_threshold=similarity_threshold,
            include_archived=include_archived, current_user=current_user,
        )

    return _execute_with_query_expansion(
        trimmed, limit,
        {"search_type": "semantic",
         "agent_id": str(agent_id) if agent_id else None,
         "conversation_id": str(conversation_id) if conversation_id else None,
         "similarity_threshold": similarity_threshold},
        _runner, "semantic",
    )


def search_memory_blocks_hybrid(
    db: Session,
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    fulltext_weight: float = 0.7,
    semantic_weight: float = 0.3,
    min_combined_score: float = 0.1,
    include_archived: bool = False,
    *,
    current_user: Optional[Dict[str, Any]] = None,
) -> Tuple[List["schemas.MemoryBlockWithScore"], Dict[str, Any]]:
    """Hybrid search with optional query expansion."""
    svc = get_search_service()
    trimmed = (query or "").strip()
    if not trimmed:
        return [], {"search_type": "hybrid", "message": "Empty query"}

    def _runner(q):
        return svc.search_memory_blocks_hybrid(
            db=db, query=q, agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, fulltext_weight=fulltext_weight,
            semantic_weight=semantic_weight, min_combined_score=min_combined_score,
            include_archived=include_archived, current_user=current_user,
        )

    return _execute_with_query_expansion(
        trimmed, limit,
        {"search_type": "hybrid",
         "agent_id": str(agent_id) if agent_id else None,
         "conversation_id": str(conversation_id) if conversation_id else None,
         "fulltext_weight": fulltext_weight,
         "semantic_weight": semantic_weight},
        _runner, "hybrid",
    )


def search_memory_blocks_enhanced(
    db: Session,
    search_type: str = "basic",
    search_query: Optional[str] = None,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    include_archived: bool = False,
    **search_params,
) -> Tuple[List["schemas.MemoryBlockWithScore"], Dict[str, Any]]:
    """Dispatcher that routes to fulltext/semantic/hybrid/basic search."""
    svc = get_search_service()
    current_user = search_params.get("current_user")

    if search_type == "fulltext":
        return search_memory_blocks_fulltext(
            db=db, query=search_query or "", agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, min_score=search_params.get("min_score", 0.1),
            include_archived=include_archived, current_user=current_user,
        )
    if search_type == "semantic":
        return search_memory_blocks_semantic(
            db=db, query=search_query or "", agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, similarity_threshold=search_params.get("similarity_threshold", 0.7),
            include_archived=include_archived, current_user=current_user,
        )
    if search_type == "hybrid":
        return search_memory_blocks_hybrid(
            db=db, query=search_query or "", agent_id=agent_id, conversation_id=conversation_id,
            limit=limit, fulltext_weight=search_params.get("fulltext_weight", 0.7),
            semantic_weight=search_params.get("semantic_weight", 0.3),
            min_combined_score=search_params.get("min_combined_score", 0.1),
            include_archived=include_archived, current_user=current_user,
        )

    return svc.enhanced_search_memory_blocks(
        db=db, search_type=search_type, search_query=search_query,
        agent_id=agent_id, conversation_id=conversation_id,
        limit=limit, include_archived=include_archived, **search_params,
    )
