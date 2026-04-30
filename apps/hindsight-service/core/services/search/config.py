"""
Hybrid ranking configuration: dataclass, env helpers, and cache accessors.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional

from core.utils.scopes import SCOPE_PUBLIC, SCOPE_ORGANIZATION, SCOPE_PERSONAL


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
