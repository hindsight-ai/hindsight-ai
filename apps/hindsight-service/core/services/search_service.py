"""
Search service for memory blocks: full-text, semantic, and hybrid.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_, String, literal, cast, Float
from core.utils.scopes import SCOPE_PUBLIC, SCOPE_ORGANIZATION, SCOPE_PERSONAL

from core.db import models, schemas
from core.db.types import HAS_PGVECTOR
from core.services import get_embedding_service

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    """Return an environment-backed boolean with sensible parsing."""
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _env_float(name: str, default: float) -> float:
    """Return a float sourced from the environment when available."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    """Return an integer sourced from the environment when available."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class HybridRankingConfig:
    """Runtime configuration for hybrid search ranking."""

    default_fulltext_weight: float
    default_semantic_weight: float
    allow_weight_overrides: bool
    normalization_method: str
    min_score_floor: float
    feedback_boost_enabled: bool
    feedback_weight: float
    feedback_max_score: float
    recency_decay_enabled: bool
    recency_half_life_days: float
    recency_min_multiplier: float
    recency_max_multiplier: float
    scope_boost_enabled: bool
    scope_personal_bonus: float
    scope_organization_bonus: float
    scope_public_bonus: float
    reranker_enabled: bool
    reranker_provider: Optional[str]
    reranker_top_k: int

    @property
    def scope_bonus_map(self) -> Dict[str, float]:
        return {
            SCOPE_PERSONAL: self.scope_personal_bonus,
            SCOPE_ORGANIZATION: self.scope_organization_bonus,
            SCOPE_PUBLIC: self.scope_public_bonus,
        }


@lru_cache(maxsize=1)
def get_hybrid_ranking_config() -> HybridRankingConfig:
    """Read hybrid ranking configuration from environment with caching."""

    default_fulltext_weight = _env_float("HYBRID_FULLTEXT_WEIGHT", 0.7)
    default_semantic_weight = _env_float("HYBRID_SEMANTIC_WEIGHT", 0.3)
    if default_fulltext_weight < 0:
        default_fulltext_weight = 0.0
    if default_semantic_weight < 0:
        default_semantic_weight = 0.0

    return HybridRankingConfig(
        default_fulltext_weight=default_fulltext_weight,
        default_semantic_weight=default_semantic_weight,
        allow_weight_overrides=_env_bool("HYBRID_ALLOW_WEIGHT_OVERRIDES", True),
        normalization_method=os.getenv("HYBRID_NORMALIZATION", "min_max"),
        min_score_floor=_env_float("HYBRID_MIN_SCORE_FLOOR", 0.0),
        feedback_boost_enabled=_env_bool("HYBRID_FEEDBACK_BOOST_ENABLED", True),
        feedback_weight=_env_float("HYBRID_FEEDBACK_WEIGHT", 0.05),
        feedback_max_score=_env_float("HYBRID_FEEDBACK_MAX_SCORE", 100.0),
        recency_decay_enabled=_env_bool("HYBRID_RECENCY_DECAY_ENABLED", True),
        recency_half_life_days=_env_float("HYBRID_RECENCY_HALF_LIFE_DAYS", 30.0),
        recency_min_multiplier=_env_float("HYBRID_RECENCY_MIN_MULTIPLIER", 0.25),
        recency_max_multiplier=_env_float("HYBRID_RECENCY_MAX_MULTIPLIER", 1.15),
        scope_boost_enabled=_env_bool("HYBRID_SCOPE_BOOST_ENABLED", True),
        scope_personal_bonus=_env_float("HYBRID_SCOPE_PERSONAL_BONUS", 0.05),
        scope_organization_bonus=_env_float("HYBRID_SCOPE_ORG_BONUS", 0.02),
        scope_public_bonus=_env_float("HYBRID_SCOPE_PUBLIC_BONUS", 0.0),
        reranker_enabled=_env_bool("HYBRID_RERANKER_ENABLED", False),
        reranker_provider=os.getenv("HYBRID_RERANKER_PROVIDER"),
        reranker_top_k=_env_int("HYBRID_RERANKER_TOP_K", 5),
    )


def refresh_hybrid_ranking_config() -> None:
    """Clear cached hybrid ranking configuration (useful for tests)."""

    get_hybrid_ranking_config.cache_clear()


def _create_memory_block_with_score(
    memory_block: models.MemoryBlock,
    score: float,
    search_type: str,
    rank_explanation: Optional[str] = None,
    score_components: Optional[Dict[str, float]] = None,
) -> schemas.MemoryBlockWithScore:
    """
    Convert a MemoryBlock model to a MemoryBlockWithScore schema with search metadata.
    """
    # Convert keywords from SQLAlchemy models to Pydantic schemas
    keywords_list = []
    for keyword in memory_block.keywords:
        keywords_list.append(schemas.Keyword(
            keyword_id=keyword.keyword_id,
            keyword_text=keyword.keyword_text,
            created_at=keyword.created_at
        ))
    
    # Convert the MemoryBlock to dict, then add search-specific fields
    memory_block_dict = {
        'id': memory_block.id,
        'agent_id': memory_block.agent_id,
        'conversation_id': memory_block.conversation_id,
        'content': memory_block.content,
        'errors': memory_block.errors,
        'lessons_learned': memory_block.lessons_learned,
        'metadata_col': memory_block.metadata_col,
        'feedback_score': memory_block.feedback_score,
        'archived': memory_block.archived,
        'archived_at': memory_block.archived_at,
        'timestamp': memory_block.timestamp,
        'created_at': memory_block.created_at,
        'updated_at': memory_block.updated_at,
        'keywords': keywords_list,  # Use converted keywords
        'search_score': score,
        'search_type': search_type,
        'rank_explanation': rank_explanation,
        'score_components': score_components or {},
    }

    return schemas.MemoryBlockWithScore(**memory_block_dict)


class SearchService:
    """Service for handling different types of memory block searches."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
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
        """
        Perform BM25-like full-text search using PostgreSQL's built-in capabilities.
        
        Args:
            db: Database session
            query: Search query string
            agent_id: Optional agent filter
            conversation_id: Optional conversation filter
            limit: Maximum number of results
            min_score: Minimum relevance score threshold
            include_archived: Whether to include archived memory blocks
            
        Returns:
            Tuple of (results, metadata)
        """
        start_time = time.time()
        
        try:
            # If we're not on PostgreSQL (e.g., SQLite test environment), fall back to basic search
            dialect_name = getattr(db.bind.dialect, 'name', '') if getattr(db, 'bind', None) else ''
            if dialect_name != 'postgresql':
                # Use basic fallback (substring/ILIKE) to keep tests green and still exercise search flow
                fallback_results, meta = self._basic_search_fallback(
                    db, query, agent_id, conversation_id, limit, include_archived, current_user
                )
                meta.update({
                    'search_type': 'fulltext_fallback',
                    'fallback_reason': f'dialect {dialect_name} does not support PostgreSQL full-text',
                })
                return fallback_results, meta
            # Convert query to tsquery format
            # Use plainto_tsquery for simple queries, websearch_to_tsquery for advanced
            search_query_func = func.plainto_tsquery('english', query)
            
            # If query contains operators, use websearch_to_tsquery
            if any(op in query.lower() for op in ['and', 'or', 'not', '"']):
                search_query_func = func.websearch_to_tsquery('english', query)
            
            # Build base query with ranking using the pre-computed search_vector
            # Use ts_rank_cd for better ranking that considers document length
            rank_expression = func.ts_rank_cd(
                models.MemoryBlock.search_vector,
                search_query_func
            )
            
            base_query = db.query(
                models.MemoryBlock,
                rank_expression.label('rank')
            ).filter(
                models.MemoryBlock.search_vector.op('@@')(search_query_func)
            ).filter(
                rank_expression >= min_score
            )

            # Scope filters
            if current_user is None:
                base_query = base_query.filter(models.MemoryBlock.visibility_scope == SCOPE_PUBLIC)
            else:
                org_ids: List[uuid.UUID] = []
                for m in (current_user.get('memberships') or []):
                    try:
                        org_ids.append(uuid.UUID(m.get('organization_id')))
                    except Exception:
                        pass
                base_query = base_query.filter(
                    or_(
                        models.MemoryBlock.visibility_scope == SCOPE_PUBLIC,
                        models.MemoryBlock.owner_user_id == current_user.get('id'),
                        and_(
                            models.MemoryBlock.visibility_scope == SCOPE_ORGANIZATION,
                            models.MemoryBlock.organization_id.in_(org_ids) if org_ids else False,
                        ),
                    )
                )
            
            # Apply filters
            if agent_id:
                base_query = base_query.filter(models.MemoryBlock.agent_id == agent_id)
            
            if conversation_id:
                base_query = base_query.filter(models.MemoryBlock.conversation_id == conversation_id)
            
            # Handle archived filter
            if not include_archived:
                base_query = base_query.filter(
                    or_(
                        models.MemoryBlock.archived == False,
                        models.MemoryBlock.archived.is_(None)
                    )
                )
            
            # Order by relevance and limit
            results_with_rank = base_query.order_by(
                rank_expression.desc(),
                models.MemoryBlock.created_at.desc()  # Secondary sort for ties
            ).limit(limit).all()
            
            # Extract memory blocks and prepare results with scores
            memory_blocks_with_scores = []
            
            for memory_block, rank in results_with_rank:
                score = float(rank) if rank else 0.0
                memory_block_with_score = _create_memory_block_with_score(
                    memory_block, score, "fulltext", 
                    f"BM25 relevance score: {score:.4f}",
                    {"fulltext_raw": score}
                )
                memory_blocks_with_scores.append(memory_block_with_score)
            
            search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            metadata = {
                "total_search_time_ms": search_time,
                "fulltext_results_count": len(memory_blocks_with_scores),
                "query_terms": query.split(),
                "search_type": "fulltext",
                "min_score_threshold": min_score
            }
            
            self.logger.info(f"Full-text search for '{query}' returned {len(memory_blocks_with_scores)} results in {search_time:.2f}ms")
            
            return memory_blocks_with_scores, metadata
            
        except Exception as e:
            self.logger.error(f"Error in full-text search: {str(e)}")
            raise
    
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
        """Run semantic search using pgvector similarity when available."""

        start_time = time.time()

        # Guard empty queries (mirrors enhanced search behaviour)
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
            results, metadata = self._basic_search_fallback(
                db,
                query,
                agent_id,
                conversation_id,
                limit,
                include_archived,
                current_user,
            )
            metadata.update(
                {
                    "search_type": "semantic_fallback",
                    "fallback_reason": "embedding_provider_disabled",
                    "similarity_threshold": similarity_threshold,
                }
            )
            return results, metadata

        if not HAS_PGVECTOR:
            results, metadata = self._basic_search_fallback(
                db,
                query,
                agent_id,
                conversation_id,
                limit,
                include_archived,
                current_user,
            )
            metadata.update(
                {
                    "search_type": "semantic_fallback",
                    "fallback_reason": "pgvector_unavailable",
                    "similarity_threshold": similarity_threshold,
                }
            )
            return results, metadata

        try:
            raw_embedding = embedding_service.embed_text(query.strip())
            if raw_embedding:
                try:
                    query_embedding = [float(value) for value in raw_embedding]
                except (TypeError, ValueError) as exc:
                    self.logger.error(
                        "Invalid embedding vector returned for semantic query '%s': %s",
                        query,
                        exc,
                    )
                    query_embedding = None
            else:
                query_embedding = None
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("Failed to embed semantic query '%s': %s", query, exc)
            query_embedding = None

        if not query_embedding:
            results, metadata = self._basic_search_fallback(
                db,
                query,
                agent_id,
                conversation_id,
                limit,
                include_archived,
                current_user,
            )
            metadata.update(
                {
                    "search_type": "semantic_fallback",
                    "fallback_reason": "query_embedding_unavailable",
                    "similarity_threshold": similarity_threshold,
                }
            )
            return results, metadata

        dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
        dialect_name = getattr(dialect_name, "name", "") if dialect_name else ""

        if dialect_name != "postgresql":
            results, metadata = self._basic_search_fallback(
                db,
                query,
                agent_id,
                conversation_id,
                limit,
                include_archived,
                current_user,
            )
            metadata.update(
                {
                    "search_type": "semantic_fallback",
                    "fallback_reason": f"dialect_{dialect_name}_unsupported",
                    "similarity_threshold": similarity_threshold,
                }
            )
            return results, metadata

        # Ensure threshold respects cosine similarity bounds [-1, 1]
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

        # Scope filters (mirrors fulltext path)
        if current_user is None:
            base_query = base_query.filter(models.MemoryBlock.visibility_scope == SCOPE_PUBLIC)
        else:
            org_ids: List[uuid.UUID] = []
            for membership in (current_user.get("memberships") or []):
                try:
                    org_ids.append(uuid.UUID(membership.get("organization_id")))
                except Exception:
                    continue
            base_query = base_query.filter(
                or_(
                    models.MemoryBlock.visibility_scope == SCOPE_PUBLIC,
                    models.MemoryBlock.owner_user_id == current_user.get("id"),
                    and_(
                        models.MemoryBlock.visibility_scope == SCOPE_ORGANIZATION,
                        models.MemoryBlock.organization_id.in_(org_ids) if org_ids else False,
                    ),
                )
            )

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

        # Apply similarity threshold and ordering (higher similarity first)
        base_query = (
            base_query.filter(distance_expr <= max_distance)
            .order_by(distance_expr.asc(), models.MemoryBlock.created_at.desc())
            .limit(limit)
        )

        try:
            results_with_similarity = base_query.all()
        except Exception as exc:  # pragma: no cover - defensive database failure
            self.logger.error("Semantic search query failed: %s", exc)
            fallback_results, metadata = self._basic_search_fallback(
                db,
                query,
                agent_id,
                conversation_id,
                limit,
                include_archived,
                current_user,
            )
            metadata.update(
                {
                    "search_type": "semantic_fallback",
                    "fallback_reason": "semantic_query_error",
                    "similarity_threshold": threshold,
                }
            )
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
                    {"semantic_raw": score, "distance": float(distance) if distance is not None else None}
                )
            )

        if not memory_blocks_with_scores:
            fallback_results, metadata = self._basic_search_fallback(
                db,
                query,
                agent_id,
                conversation_id,
                limit,
                include_archived,
                current_user,
            )
            metadata.update(
                {
                    "search_type": "semantic_fallback",
                    "fallback_reason": "no_semantic_matches",
                    "similarity_threshold": threshold,
                }
            )
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
        """
        Combine full-text and semantic search with weighted scoring and heuristics.
        """
        start_time = time.time()

        config = get_hybrid_ranking_config()
        effective_fulltext_weight, effective_semantic_weight = self._resolve_component_weights(
            fulltext_weight,
            semantic_weight,
            config,
        )

        # Get results from both search methods
        fulltext_results, fulltext_metadata = self.search_memory_blocks_fulltext(
            db, query, agent_id, conversation_id, limit * 2,  # Get more for reranking
            min_score=0.01, include_archived=include_archived, current_user=current_user  # Lower threshold for hybrid
        )

        # If the fulltext path already fell back (non-Postgres dialect), treat this as a basic-only hybrid
        if fulltext_metadata.get('search_type') == 'fulltext_fallback':
            # Return truncated fallback results with adjusted metadata; semantic still placeholder empty
            final_results = fulltext_results[:limit]
            search_time = (time.time() - start_time) * 1000
            metadata = {
                'total_search_time_ms': search_time,
                'fulltext_results_count': len(fulltext_results),
                'semantic_results_count': 0,
                'hybrid_weights': {
                    'fulltext': effective_fulltext_weight,
                    'semantic': effective_semantic_weight,
                },
                'combined_results_count': len(final_results),
                'search_type': 'hybrid_fallback',
                'fallback_reason': fulltext_metadata.get('fallback_reason'),
                'min_combined_score': min_combined_score,
                'component_summary': {
                    'fallback': True,
                    'reason': fulltext_metadata.get('fallback_reason'),
                    'weights': {
                        'fulltext': effective_fulltext_weight,
                        'semantic': effective_semantic_weight,
                        'allow_overrides': config.allow_weight_overrides,
                    },
                    'heuristics_enabled': {
                        'recency': config.recency_decay_enabled,
                        'feedback': config.feedback_boost_enabled,
                        'scope': config.scope_boost_enabled,
                        'reranker': config.reranker_enabled,
                    },
                    'requested_weights': {
                        'fulltext': fulltext_weight,
                        'semantic': semantic_weight,
                    },
                },
            }
            return final_results, metadata

        semantic_results, semantic_metadata = self.search_memory_blocks_semantic(
            db, query, agent_id, conversation_id, limit * 2,
            similarity_threshold=0.5, include_archived=include_archived, current_user=current_user
        )
        
        # If fulltext returned nothing (e.g., search_vector unpopulated), fall back to basic substring search
        if not fulltext_results:
            basic_results, _ = self._basic_search_fallback(
                db, query, agent_id, conversation_id, limit * 2, include_archived, current_user
            )
            fulltext_results = basic_results

        # Combine and rerank results
        combined_results, component_stats = self._combine_and_rerank_with_scores(
            fulltext_results, semantic_results,
            effective_fulltext_weight, effective_semantic_weight, min_combined_score,
            config=config,
        )

        # Limit final results
        final_results = combined_results[:limit]

        search_time = (time.time() - start_time) * 1000

        metadata = {
            "total_search_time_ms": search_time,
            "fulltext_results_count": len(fulltext_results),
            "semantic_results_count": len(semantic_results),
            "hybrid_weights": {
                "fulltext": effective_fulltext_weight,
                "semantic": effective_semantic_weight,
            },
            "combined_results_count": len(final_results),
            "search_type": "hybrid",
            "min_combined_score": min_combined_score,
            "component_summary": {
                **component_stats,
                "requested_weights": {
                    "fulltext": fulltext_weight,
                    "semantic": semantic_weight,
                },
            },
            "normalization_method": config.normalization_method,
        }

        self.logger.info(f"Hybrid search for '{query}' combined {len(fulltext_results)} fulltext + {len(semantic_results)} semantic results into {len(final_results)} final results")

        return final_results, metadata
    
    def _combine_and_rerank_with_scores(
        self,
        fulltext_results: List[schemas.MemoryBlockWithScore],
        semantic_results: List[schemas.MemoryBlockWithScore],
        fulltext_weight: float,
        semantic_weight: float,
        min_combined_score: float,
        config: Optional[HybridRankingConfig] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """Blend component scores, apply heuristic boosts, and return ranked results."""

        config = config or get_hybrid_ranking_config()

        fulltext_map = {r.id: r for r in fulltext_results}
        semantic_map = {r.id: r for r in semantic_results}
        all_ids = set(fulltext_map.keys()) | set(semantic_map.keys())

        ft_raw_scores = {
            mid: float(fulltext_map[mid].search_score or 0.0)
            for mid in fulltext_map
        }
        se_raw_scores = {
            mid: float(semantic_map[mid].search_score or 0.0)
            for mid in semantic_map
        }

        ft_normalized = self._normalize_component_scores(ft_raw_scores, config.normalization_method)
        se_normalized = self._normalize_component_scores(se_raw_scores, config.normalization_method)

        now = datetime.now(timezone.utc)
        scored_results: List[Tuple[schemas.MemoryBlockWithScore, float]] = []
        heuristic_totals = {
            "recency": 0.0,
            "feedback": 0.0,
            "scope": 0.0,
            "reranker": 0.0,
        }

        for mid in all_ids:
            base_result = fulltext_map.get(mid) or semantic_map[mid]
            ft_raw = ft_raw_scores.get(mid, 0.0)
            se_raw = se_raw_scores.get(mid, 0.0)
            ft_norm = ft_normalized.get(mid, 0.0)
            se_norm = se_normalized.get(mid, 0.0)

            weighted_fulltext = ft_norm * fulltext_weight
            weighted_semantic = se_norm * semantic_weight
            base_weighted = weighted_fulltext + weighted_semantic

            recency_multiplier = 1.0
            recency_adjustment = 0.0
            if config.recency_decay_enabled:
                recency_multiplier = self._recency_multiplier(getattr(base_result, "timestamp", None), config, now)
                recency_adjustment = base_weighted * (recency_multiplier - 1.0)
            score_after_recency = base_weighted * recency_multiplier

            feedback_adjustment = 0.0
            if config.feedback_boost_enabled:
                feedback_adjustment = self._feedback_adjustment(getattr(base_result, "feedback_score", 0), config)
            score_after_feedback = score_after_recency + feedback_adjustment

            scope_boost = 0.0
            if config.scope_boost_enabled:
                scope_value = getattr(base_result, "visibility_scope", None)
                scope_boost = float(config.scope_bonus_map.get(scope_value, 0.0))
            score_before_reranker = score_after_feedback + scope_boost

            reranker_adjustment = 0.0
            # Placeholder for future reranker integration; keep slot in components/metadata.
            final_score = max(score_before_reranker + reranker_adjustment, config.min_score_floor)

            heuristic_totals["recency"] += recency_adjustment
            heuristic_totals["feedback"] += feedback_adjustment
            heuristic_totals["scope"] += scope_boost
            heuristic_totals["reranker"] += reranker_adjustment

            if final_score < min_combined_score:
                continue

            components = {
                "fulltext_raw": ft_raw,
                "semantic_raw": se_raw,
                "fulltext_normalized": ft_norm,
                "semantic_normalized": se_norm,
                "weighted_fulltext": weighted_fulltext,
                "weighted_semantic": weighted_semantic,
                "base_weighted_score": base_weighted,
                "recency_multiplier": recency_multiplier,
                "recency_adjustment": recency_adjustment,
                "feedback_boost": feedback_adjustment,
                "scope_boost": scope_boost,
                "reranker_adjustment": reranker_adjustment,
            }

            rank_explanation = self._format_rank_explanation(final_score, components, fulltext_weight, semantic_weight)
            result_copy = base_result.model_copy()
            result_copy.search_score = final_score
            result_copy.search_type = "hybrid"
            result_copy.rank_explanation = rank_explanation
            result_copy.score_components = components
            scored_results.append((result_copy, final_score))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        ranked_results = [result for result, _ in scored_results]

        stats = {
            "weights": {
                "fulltext": fulltext_weight,
                "semantic": semantic_weight,
                "allow_overrides": config.allow_weight_overrides,
            },
            "normalization": {
                "method": config.normalization_method,
                "fulltext_raw_min": min(ft_raw_scores.values(), default=None),
                "fulltext_raw_max": max(ft_raw_scores.values(), default=None),
                "semantic_raw_min": min(se_raw_scores.values(), default=None),
                "semantic_raw_max": max(se_raw_scores.values(), default=None),
            },
            "heuristics_enabled": {
                "recency": config.recency_decay_enabled,
                "feedback": config.feedback_boost_enabled,
                "scope": config.scope_boost_enabled,
                "reranker": config.reranker_enabled,
            },
            "heuristic_totals": heuristic_totals,
            "candidate_counts": {
                "fulltext": len(fulltext_results),
                "semantic": len(semantic_results),
                "union": len(all_ids),
            },
        }

        return ranked_results, stats

    @staticmethod
    def _normalize_component_scores(
        scores: Dict[uuid.UUID, float],
        method: str,
    ) -> Dict[uuid.UUID, float]:
        """Normalize scores according to the requested method."""

        if not scores:
            return {}

        if method == "max":
            max_score = max(scores.values())
            if max_score <= 0:
                return {mid: 0.0 for mid in scores}
            return {mid: max(score / max_score, 0.0) for mid, score in scores.items()}

        # Default to min-max normalization.
        min_score = min(scores.values())
        max_score = max(scores.values())
        if max_score == min_score:
            baseline = 1.0 if max_score > 0 else 0.0
            return {mid: baseline for mid in scores}

        delta = max_score - min_score
        normalized = {}
        for mid, score in scores.items():
            value = (score - min_score) / delta
            if value < 0.0:
                value = 0.0
            elif value > 1.0:
                value = 1.0
            normalized[mid] = value
        return normalized

    @staticmethod
    def _resolve_component_weights(
        requested_fulltext: Optional[float],
        requested_semantic: Optional[float],
        config: HybridRankingConfig,
    ) -> Tuple[float, float]:
        """Normalize requested weights while respecting configuration defaults."""

        if not config.allow_weight_overrides:
            requested_fulltext = config.default_fulltext_weight
            requested_semantic = config.default_semantic_weight

        use_config_defaults = (
            (requested_fulltext is None and requested_semantic is None)
            or (
                requested_fulltext == 0.7
                and requested_semantic == 0.3
                and (
                    config.default_fulltext_weight != 0.7
                    or config.default_semantic_weight != 0.3
                )
            )
        )

        fulltext_value = (
            config.default_fulltext_weight
            if use_config_defaults
            else (requested_fulltext if requested_fulltext is not None else config.default_fulltext_weight)
        )
        semantic_value = (
            config.default_semantic_weight
            if use_config_defaults
            else (requested_semantic if requested_semantic is not None else config.default_semantic_weight)
        )

        fulltext_value = max(fulltext_value or 0.0, 0.0)
        semantic_value = max(semantic_value or 0.0, 0.0)

        total = fulltext_value + semantic_value
        if total <= 0:
            fulltext_value = config.default_fulltext_weight or 0.5
            semantic_value = config.default_semantic_weight or 0.5
            total = fulltext_value + semantic_value
            if total <= 0:
                return 0.5, 0.5

        normalized_fulltext = fulltext_value / total
        normalized_semantic = semantic_value / total
        return normalized_fulltext, normalized_semantic

    @staticmethod
    def _recency_multiplier(
        timestamp: Optional[datetime],
        config: HybridRankingConfig,
        now: datetime,
    ) -> float:
        """Return an exponential decay multiplier favouring recent memories."""

        if not timestamp or not isinstance(timestamp, datetime):
            return 1.0

        block_time = timestamp
        if block_time.tzinfo is None:
            block_time = block_time.replace(tzinfo=timezone.utc)
        else:
            block_time = block_time.astimezone(timezone.utc)

        if block_time > now:
            block_time = now

        half_life = max(config.recency_half_life_days, 0.0001)
        age_days = (now - block_time).total_seconds() / 86400.0
        multiplier = 0.5 ** (age_days / half_life)
        return max(min(multiplier, config.recency_max_multiplier), config.recency_min_multiplier)

    @staticmethod
    def _feedback_adjustment(
        feedback_score: Optional[int],
        config: HybridRankingConfig,
    ) -> float:
        """Translate stored feedback into an additive boost."""

        if feedback_score is None:
            return 0.0

        max_score = max(config.feedback_max_score, 1.0)
        normalized = max(min(float(feedback_score) / max_score, 1.0), -1.0)
        return normalized * config.feedback_weight

    @staticmethod
    def _format_rank_explanation(
        final_score: float,
        components: Dict[str, float],
        fulltext_weight: float,
        semantic_weight: float,
    ) -> str:
        """Build a compact explanation string highlighting component impacts."""

        parts = [
            (
                "Hybrid score {final:.4f} = (fulltext_norm {ft_norm:.4f} * {ft_w:.2f}) "
                "+ (semantic_norm {se_norm:.4f} * {se_w:.2f})"
            ).format(
                final=final_score,
                ft_norm=components.get("fulltext_normalized", 0.0),
                ft_w=fulltext_weight,
                se_norm=components.get("semantic_normalized", 0.0),
                se_w=semantic_weight,
            )
        ]

        adjustments = []
        recency_adj = components.get("recency_adjustment", 0.0)
        if abs(recency_adj) > 1e-6:
            adjustments.append(f"recency {recency_adj:+.4f}")

        feedback_adj = components.get("feedback_boost", 0.0)
        if abs(feedback_adj) > 1e-6:
            adjustments.append(f"feedback {feedback_adj:+.4f}")

        scope_adj = components.get("scope_boost", 0.0)
        if abs(scope_adj) > 1e-6:
            adjustments.append(f"scope {scope_adj:+.4f}")

        reranker_adj = components.get("reranker_adjustment", 0.0)
        if abs(reranker_adj) > 1e-6:
            adjustments.append(f"reranker {reranker_adj:+.4f}")

        if adjustments:
            parts.append("; " + ", ".join(adjustments))

        return "".join(parts)

    # Helper used by tests: accepts raw items + separate score lists
    def _combine_and_rerank(
        self,
        fulltext_items: List[Any],
        semantic_items: List[Any],
        fulltext_scores: List[float],
        semantic_scores: List[float],
        fulltext_weight: float,
        semantic_weight: float,
        min_combined_score: float,
    ) -> List[Any]:
        ft_map = {}
        for item, score in zip(fulltext_items, fulltext_scores):
            ft_map[getattr(item, 'id', id(item))] = (item, score)
        se_map = {}
        for item, score in zip(semantic_items, semantic_scores):
            se_map[getattr(item, 'id', id(item))] = (item, score)

        all_ids = set(ft_map.keys()) | set(se_map.keys())
        scored: List[tuple[Any, float]] = []
        for mid in all_ids:
            ft_score = ft_map.get(mid, (None, 0.0))[1]
            se_score = se_map.get(mid, (None, 0.0))[1]
            combined = ft_score * fulltext_weight + se_score * semantic_weight
            if combined >= min_combined_score:
                base = (ft_map.get(mid) or se_map.get(mid))[0]
                # Attach combined score attribute for callers that inspect it
                try:
                    setattr(base, 'search_score', combined)
                except Exception:
                    pass
                scored.append((base, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored]
    
    def enhanced_search_memory_blocks(
        self,
        db: Session,
        search_query: Optional[str] = None,
        search_type: str = "basic",
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        include_archived: bool = False,
        **search_params
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """
        Enhanced search method that supports multiple search types.
        
        Args:
            db: Database session
            search_type: Type of search ("basic", "fulltext", "semantic", "hybrid")
            search_query: Search query string
            agent_id: Optional agent filter
            conversation_id: Optional conversation filter
            limit: Maximum number of results
            include_archived: Whether to include archived blocks
            **search_params: Additional search parameters
            
        Returns:
            Tuple of (results, metadata)
        """
        if not search_query or search_query.strip() == "":
            # Return empty results for empty queries
            return [], {"search_type": search_type, "message": "Empty query"}
        
        if search_type == "fulltext":
            return self.search_memory_blocks_fulltext(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("min_score", 0.1), include_archived
            )
        elif search_type == "semantic":
            return self.search_memory_blocks_semantic(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("similarity_threshold", 0.7), include_archived
            )
        elif search_type == "hybrid":
            return self.search_memory_blocks_hybrid(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("fulltext_weight", 0.7),
                search_params.get("semantic_weight", 0.3),
                search_params.get("min_combined_score", 0.1), include_archived
            )
        else:
            # Fall back to basic search (existing ILIKE implementation)
            return self._basic_search_fallback(
                db,
                search_query,
                agent_id,
                conversation_id,
                limit,
                include_archived,
                search_params.get('current_user'),
                keyword_terms=search_params.get('keyword_list'),
                match_any=bool(search_params.get('match_any')),
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
        """
        Fallback to basic ILIKE search for backward compatibility.
        """
        start_time = time.time()
        
        # Build search filters using ILIKE (case-insensitive substring search)
        explicit_terms = [term.strip() for term in (keyword_terms or []) if term and term.strip()]
        search_terms = explicit_terms or search_query.split()
        search_filters = []

        for term in search_terms:
            term_filter = or_(
                models.MemoryBlock.content.ilike(f"%{term}%"),
                models.MemoryBlock.errors.ilike(f"%{term}%"),
                models.MemoryBlock.lessons_learned.ilike(f"%{term}%"),
                models.MemoryBlock.id.cast(String).ilike(f"%{term}%")
            )
            search_filters.append(term_filter)

        # Combine all search filters with AND logic
        if search_filters:
            combined_filter = or_(*search_filters) if match_any else and_(*search_filters)
        else:
            combined_filter = None
        
        query = db.query(models.MemoryBlock)
        
        if combined_filter is not None:
            query = query.filter(combined_filter)
        
        # Apply scope filters
        if current_user is None:
            # Internal callers (e.g., agent tools) may not provide a user context but do
            # pass an agent/conversation filter. In that case we retain historical
            # behaviour and search across the agent's entire corpus regardless of
            # visibility. Only default to public-only results when no scope hints are
            # supplied.
            if not agent_id and not conversation_id:
                query = query.filter(models.MemoryBlock.visibility_scope == SCOPE_PUBLIC)
        else:
            org_ids: List[uuid.UUID] = []
            for m in (current_user.get('memberships') or []):
                try:
                    org_ids.append(uuid.UUID(m.get('organization_id')))
                except Exception:
                    pass
            query = query.filter(
                or_(
                    models.MemoryBlock.visibility_scope == SCOPE_PUBLIC,
                    models.MemoryBlock.owner_user_id == current_user.get('id'),
                    and_(
                        models.MemoryBlock.visibility_scope == SCOPE_ORGANIZATION,
                        models.MemoryBlock.organization_id.in_(org_ids) if org_ids else False,
                    ),
                )
            )

        # Apply additional filters
        if agent_id:
            query = query.filter(models.MemoryBlock.agent_id == agent_id)
        
        if conversation_id:
            query = query.filter(models.MemoryBlock.conversation_id == conversation_id)
        
        # Handle archived filter
        if not include_archived:
            query = query.filter(
                or_(
                    models.MemoryBlock.archived == False,
                    models.MemoryBlock.archived.is_(None)
                )
            )
        
        # Order by creation date and limit
        raw_results = query.order_by(
            models.MemoryBlock.created_at.desc()
        ).limit(limit).all()
        
        # Convert to MemoryBlockWithScore objects
        results = []
        for i, memory_block in enumerate(raw_results):
            # Basic search doesn't have a real score, so use inverted rank
            score = 1.0 - (i / (len(raw_results) + 1))  # Score from 1.0 to close to 0
            result_with_score = _create_memory_block_with_score(
                memory_block,
                score,
                "basic",
                f"Basic search result rank: {i+1}",
                {"basic_rank": float(i + 1), "basic_score": score}
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


# Global search service instance
_search_service = None


def get_search_service() -> SearchService:
    """Get or create the global search service instance."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
