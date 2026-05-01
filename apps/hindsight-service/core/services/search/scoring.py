"""
Shared scoring utilities used across search strategies.

Includes:
- _create_memory_block_with_score: model -> schema conversion with search metadata
- _apply_user_scope_filter: visibility filter mirroring scope_utils
- _normalize_component_scores: min-max / max normalization for rank fusion
- _resolve_component_weights: normalize requested hybrid weights
- _recency_multiplier: exponential decay multiplier for recent memories
- _feedback_adjustment: translate stored feedback into an additive boost
- _format_rank_explanation: compact explanation string for hybrid results
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from core.db import models, schemas
from core.utils.scopes import SCOPE_PUBLIC, SCOPE_ORGANIZATION, SCOPE_PERSONAL
from core.services.search.config import HybridRankingConfig

if TYPE_CHECKING:
    from core.api.deps import CurrentUserContext


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
        'keywords': keywords_list,
        'search_score': score,
        'search_type': search_type,
        'rank_explanation': rank_explanation,
        'score_components': score_components or {},
    }

    return schemas.MemoryBlockWithScore(**memory_block_dict)


def _apply_user_scope_filter(query, current_user: Optional["CurrentUserContext"], model_class):
    """Apply visibility filter mirroring scope_utils.apply_scope_filter.

    Treats `current_user is None` OR `current_user.id is None` as a
    guest: public-only. The latter case is critical — a malformed user context
    that lacks `id` would otherwise produce `owner_user_id == NULL`, which
    matches every organization-scoped row (NULL owner is the canonical
    org-row signature) and silently leaks all org data.
    """
    if current_user is None:
        return query.filter(model_class.visibility_scope == SCOPE_PUBLIC)
    # Defensive against malformed input (dict missing 'id', or any non-CurrentUserContext
    # value passed by a non-migrated caller). Matches scope_utils.apply_scope_filter
    # behavior — treat malformed input as guest, public-only.
    try:
        user_id = current_user.id
    except AttributeError:
        return query.filter(model_class.visibility_scope == SCOPE_PUBLIC)
    if user_id is None:
        return query.filter(model_class.visibility_scope == SCOPE_PUBLIC)

    org_ids: List[uuid.UUID] = []
    for m in (current_user.memberships or []):
        try:
            org_ids.append(uuid.UUID(m.get('organization_id')))
        except Exception:
            continue

    return query.filter(
        or_(
            model_class.visibility_scope == SCOPE_PUBLIC,
            model_class.owner_user_id == user_id,
            and_(
                model_class.visibility_scope == SCOPE_ORGANIZATION,
                model_class.organization_id.in_(org_ids) if org_ids else False,
            ),
        )
    )


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
