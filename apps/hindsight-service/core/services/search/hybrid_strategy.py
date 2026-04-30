"""
Hybrid search strategy: fuses fulltext + semantic results with weighted scoring
and configurable heuristic boosts (recency, feedback, scope, reranker slot).
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy.orm import Session

from core.db import schemas
from core.services.search.base import SearchStrategy
from core.services.search.config import HybridRankingConfig, get_hybrid_ranking_config
from core.services.search.scoring import (
    _normalize_component_scores,
    _resolve_component_weights,
    _recency_multiplier,
    _feedback_adjustment,
    _format_rank_explanation,
)

if TYPE_CHECKING:
    from core.api.deps import CurrentUserContext

logger = logging.getLogger(__name__)


class HybridSearchStrategy(SearchStrategy):
    """Combines fulltext and semantic results using rank fusion and heuristic boosts."""

    def __init__(
        self,
        fulltext_strategy: SearchStrategy,
        semantic_strategy: SearchStrategy,
        basic_strategy: SearchStrategy,
    ):
        self._fulltext = fulltext_strategy
        self._semantic = semantic_strategy
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
        fulltext_weight: float = 0.7,
        semantic_weight: float = 0.3,
        min_combined_score: float = 0.1,
        **kwargs: Any,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """Blend fulltext + semantic results; apply recency/feedback/scope boosts."""
        start_time = time.time()

        config = get_hybrid_ranking_config()
        effective_fulltext_weight, effective_semantic_weight = _resolve_component_weights(
            fulltext_weight,
            semantic_weight,
            config,
        )

        fulltext_results, fulltext_metadata = self._fulltext.search(
            db, query,
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit * 2,
            min_score=0.01,
            include_archived=include_archived,
            current_user=current_user,
        )

        # If fulltext already fell back (non-Postgres), return truncated fallback
        if fulltext_metadata.get("search_type") == "fulltext_fallback":
            final_results = fulltext_results[:limit]
            search_time = (time.time() - start_time) * 1000
            metadata = {
                "total_search_time_ms": search_time,
                "fulltext_results_count": len(fulltext_results),
                "semantic_results_count": 0,
                "hybrid_weights": {
                    "fulltext": effective_fulltext_weight,
                    "semantic": effective_semantic_weight,
                },
                "combined_results_count": len(final_results),
                "search_type": "hybrid_fallback",
                "fallback_reason": fulltext_metadata.get("fallback_reason"),
                "min_combined_score": min_combined_score,
                "component_summary": {
                    "fallback": True,
                    "reason": fulltext_metadata.get("fallback_reason"),
                    "weights": {
                        "fulltext": effective_fulltext_weight,
                        "semantic": effective_semantic_weight,
                        "allow_overrides": config.allow_weight_overrides,
                    },
                    "heuristics_enabled": {
                        "recency": config.recency_decay_enabled,
                        "feedback": config.feedback_boost_enabled,
                        "scope": config.scope_boost_enabled,
                        "reranker": config.reranker_enabled,
                    },
                    "requested_weights": {
                        "fulltext": fulltext_weight,
                        "semantic": semantic_weight,
                    },
                },
            }
            return final_results, metadata

        semantic_results, _semantic_metadata = self._semantic.search(
            db, query,
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit * 2,
            similarity_threshold=0.5,
            include_archived=include_archived,
            current_user=current_user,
        )

        # If fulltext returned nothing (e.g. search_vector unpopulated), use basic
        if not fulltext_results:
            basic_results, _ = self._basic.search(
                db, query,
                agent_id=agent_id,
                conversation_id=conversation_id,
                limit=limit * 2,
                include_archived=include_archived,
                current_user=current_user,
            )
            fulltext_results = basic_results

        combined_results, component_stats = self._combine_and_rerank_with_scores(
            fulltext_results,
            semantic_results,
            effective_fulltext_weight,
            effective_semantic_weight,
            min_combined_score,
            config=config,
        )

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

        logger.info(
            "Hybrid search for '%s' combined %d fulltext + %d semantic results into %d final results",
            query, len(fulltext_results), len(semantic_results), len(final_results),
        )

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

        ft_normalized = _normalize_component_scores(ft_raw_scores, config.normalization_method)
        se_normalized = _normalize_component_scores(se_raw_scores, config.normalization_method)

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
                recency_multiplier = _recency_multiplier(
                    getattr(base_result, "timestamp", None), config, now
                )
                recency_adjustment = base_weighted * (recency_multiplier - 1.0)
            score_after_recency = base_weighted * recency_multiplier

            feedback_adjustment = 0.0
            if config.feedback_boost_enabled:
                feedback_adjustment = _feedback_adjustment(
                    getattr(base_result, "feedback_score", 0), config
                )
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

            rank_explanation = _format_rank_explanation(
                final_score, components, fulltext_weight, semantic_weight
            )
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
        """Test-facing helper: accepts raw items + separate score lists."""
        ft_map = {}
        for item, score in zip(fulltext_items, fulltext_scores):
            ft_map[getattr(item, "id", id(item))] = (item, score)
        se_map = {}
        for item, score in zip(semantic_items, semantic_scores):
            se_map[getattr(item, "id", id(item))] = (item, score)

        all_ids = set(ft_map.keys()) | set(se_map.keys())
        scored: List[tuple] = []
        for mid in all_ids:
            ft_score = ft_map.get(mid, (None, 0.0))[1]
            se_score = se_map.get(mid, (None, 0.0))[1]
            combined = ft_score * fulltext_weight + se_score * semantic_weight
            if combined >= min_combined_score:
                base = (ft_map.get(mid) or se_map.get(mid))[0]
                try:
                    setattr(base, "search_score", combined)
                except Exception:
                    pass
                scored.append((base, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored]
