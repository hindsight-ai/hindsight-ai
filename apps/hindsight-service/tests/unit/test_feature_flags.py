import pytest

from core.utils.feature_flags import (
    FeatureFlagKey,
    get_feature_flags,
    is_feature_enabled,
    refresh_feature_flag_cache,
)

_ENV_FLAG_MAPPING = {
    "LLM_FEATURES_ENABLED": "llm_features_enabled",
    "FEATURE_CONSOLIDATION_ENABLED": "feature_consolidation_enabled",
    "FEATURE_PRUNING_ENABLED": "feature_pruning_enabled",
    "FEATURE_ARCHIVED_ENABLED": "feature_archived_enabled",
}


@pytest.fixture(autouse=True)
def reset_flags(monkeypatch):
    """Clear env + cached values for each test to avoid cross-contamination."""
    for env_name in _ENV_FLAG_MAPPING:
        monkeypatch.delenv(env_name, raising=False)
    refresh_feature_flag_cache()
    yield
    refresh_feature_flag_cache()


def test_get_feature_flags_defaults_true():
    flags = get_feature_flags()
    assert flags == {
        "llm_features_enabled": True,
        "feature_consolidation_enabled": True,
        "feature_pruning_enabled": True,
        "feature_archived_enabled": True,
    }


@pytest.mark.parametrize(
    "env_name,flag_key",
    list(_ENV_FLAG_MAPPING.items()),
)
def test_individual_flag_disabled_via_env(monkeypatch, env_name: str, flag_key: FeatureFlagKey):
    monkeypatch.setenv(env_name, "false")
    refresh_feature_flag_cache()

    flags = get_feature_flags()
    assert flags[flag_key] is False
    assert is_feature_enabled(flag_key) is False


@pytest.mark.parametrize("raw_value", ["maybe", "junk", "2", None])
def test_invalid_value_falls_back_to_default(monkeypatch, raw_value):
    env_name = "LLM_FEATURES_ENABLED"
    if raw_value is None:
        monkeypatch.delenv(env_name, raising=False)
    else:
        monkeypatch.setenv(env_name, raw_value)
    refresh_feature_flag_cache()

    assert get_feature_flags()["llm_features_enabled"] is True


def test_refresh_feature_flag_cache_forces_reload(monkeypatch):
    monkeypatch.setenv("LLM_FEATURES_ENABLED", "false")
    refresh_feature_flag_cache()
    assert get_feature_flags()["llm_features_enabled"] is False

    # Update env without clearing cache – still should read stale value
    monkeypatch.setenv("LLM_FEATURES_ENABLED", "true")
    assert get_feature_flags()["llm_features_enabled"] is False

    refresh_feature_flag_cache()
    assert get_feature_flags()["llm_features_enabled"] is True
