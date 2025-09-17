"""Feature flag helpers for runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Literal, TypedDict, cast


FeatureFlagKey = Literal[
    "llm_features_enabled",
    "feature_consolidation_enabled",
    "feature_pruning_enabled",
    "feature_archived_enabled",
]


class FeatureFlagValues(TypedDict):
    llm_features_enabled: bool
    feature_consolidation_enabled: bool
    feature_pruning_enabled: bool
    feature_archived_enabled: bool


@dataclass(frozen=True)
class FeatureFlagDefinition:
    env_var: str
    default: bool


_FEATURE_FLAG_DEFINITIONS: Dict[FeatureFlagKey, FeatureFlagDefinition] = {
    "llm_features_enabled": FeatureFlagDefinition("LLM_FEATURES_ENABLED", True),
    "feature_consolidation_enabled": FeatureFlagDefinition("FEATURE_CONSOLIDATION_ENABLED", True),
    "feature_pruning_enabled": FeatureFlagDefinition("FEATURE_PRUNING_ENABLED", True),
    "feature_archived_enabled": FeatureFlagDefinition("FEATURE_ARCHIVED_ENABLED", True),
}


def _normalize_bool(value: str | None, default: bool = True) -> bool:
    """Return normalized boolean from environment-style value."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"", "0", "false", "no", "off"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True
    return default


@lru_cache(maxsize=None)
def get_feature_flags() -> FeatureFlagValues:
    """Return the cached feature flag state sourced from the environment."""
    values: Dict[FeatureFlagKey, bool] = {}
    for key, definition in _FEATURE_FLAG_DEFINITIONS.items():
        values[key] = _normalize_bool(os.getenv(definition.env_var), default=definition.default)
    return cast(FeatureFlagValues, values)


def is_feature_enabled(flag: FeatureFlagKey) -> bool:
    """Return whether the supplied feature flag evaluates to true."""
    return get_feature_flags()[flag]


def llm_features_enabled() -> bool:
    """Global toggle for LLM-powered workflows."""
    return is_feature_enabled("llm_features_enabled")


def consolidation_feature_enabled() -> bool:
    """Toggle visibility for the consolidation surface."""
    return is_feature_enabled("feature_consolidation_enabled")


def pruning_feature_enabled() -> bool:
    """Toggle visibility for pruning workflows."""
    return is_feature_enabled("feature_pruning_enabled")


def archived_feature_enabled() -> bool:
    """Toggle visibility for archived memory browsing."""
    return is_feature_enabled("feature_archived_enabled")


def refresh_feature_flag_cache() -> None:
    """Invalidate cached feature flag values (useful for tests)."""
    get_feature_flags.cache_clear()
