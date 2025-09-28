import json
from pathlib import Path

from core.services.query_expansion import QueryExpansionConfig, QueryExpansionEngine


def _make_engine(**overrides) -> QueryExpansionEngine:
    config = QueryExpansionConfig(
        enabled=overrides.pop("enabled", True),
        stemming_enabled=overrides.pop("stemming_enabled", True),
        synonyms_enabled=overrides.pop("synonyms_enabled", True),
        llm_provider=overrides.pop("llm_provider", "mock"),
        max_expansions=overrides.pop("max_expansions", 5),
        llm_max_expansions=overrides.pop("llm_max_expansions", 2),
        synonyms_path=overrides.pop("synonyms_path", None),
        llm_model=overrides.pop("llm_model", "unused"),
        llm_base_url=overrides.pop("llm_base_url", "http://ollama:11434"),
        llm_temperature=overrides.pop("llm_temperature", 0.0),
        llm_max_tokens=overrides.pop("llm_max_tokens", 64),
        llm_timeout_seconds=overrides.pop("llm_timeout_seconds", 5.0),
    )
    if overrides:
        raise AssertionError(f"Unexpected overrides: {sorted(overrides)}")
    return QueryExpansionEngine(config=config)


def test_expand_combines_all_enabled_strategies():
    engine = _make_engine()

    result = engine.expand("optimizing database deployment reliability")

    variants = result.expanded_queries
    assert "optimiz database deployment reliability" in variants  # stemming applied
    assert "optimizing db deployment reliability" in variants  # synonym swap
    # mock provider produces deterministic rewrites that add variety
    assert any(v.endswith("explained") for v in variants)
    assert any(v.startswith("How to ") for v in variants)
    assert result.to_metadata()["expansion_applied"] is True


def test_expand_respects_max_variants():
    engine = _make_engine(max_expansions=1)

    result = engine.expand("optimizing database deployment reliability")

    assert len(result.expanded_queries) == 1
    assert result.applied_steps[0]["step"] in {"stemming", "synonym", "llm_rewrite"}


def test_expand_disabled_returns_reason():
    engine = _make_engine(enabled=False)

    result = engine.expand("anything")

    assert result.expanded_queries == []
    assert result.disabled_reason == "expansion_disabled"
    assert result.to_metadata()["expansion_applied"] is False


def test_expand_empty_query_returns_blank_result():
    engine = _make_engine()

    result = engine.expand("   ")

    assert result.original_query == ""
    assert result.expanded_queries == []


def test_custom_synonyms_file_used(tmp_path: Path):
    synonyms_file = tmp_path / "synonyms.json"
    synonyms_data = {"latency": ["response time"]}
    synonyms_file.write_text(json.dumps(synonyms_data), encoding="utf-8")

    engine = _make_engine(synonyms_path=str(synonyms_file))

    result = engine.expand("latency investigation")

    assert "response time investigation" in result.expanded_queries


def test_query_expansion_llm_mock(monkeypatch):
    engine = _make_engine(
        llm_provider="mock",
        max_expansions=4,
        synonyms_enabled=False,
        stemming_enabled=False,
    )

    result = engine.expand("reduce errors", context={"case": "llm"})

    assert any("explained" in variant for variant in result.expanded_queries)
    assert any(step["step"] == "llm_rewrite" for step in result.applied_steps)


def test_query_expansion_llm_ollama(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    captured = {}

    def fake_post(url, json=None, timeout=None):  # noqa: A002 - shadowing by design
        captured["url"] = url
        captured["payload"] = json
        captured["timeout"] = timeout
        return FakeResponse({"response": "synonym for reliability\nrobust query handling"})

    monkeypatch.setattr("core.services.query_expansion.requests.post", fake_post)

    engine = _make_engine(
        llm_provider="ollama",
        llm_model="llama3.2:1b",
        max_expansions=3,
        synonyms_enabled=False,
        stemming_enabled=False,
    )

    result = engine.expand("reliable search")

    assert captured["url"].endswith("/api/generate")
    assert captured["payload"]["model"] == "llama3.2:1b"
    assert len(result.expanded_queries) == 2
    assert all(step["step"] == "llm_rewrite" for step in result.applied_steps)
