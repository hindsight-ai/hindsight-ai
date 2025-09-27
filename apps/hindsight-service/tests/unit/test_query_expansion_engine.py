from core.services.query_expansion import QueryExpansionConfig, QueryExpansionEngine


def build_engine(**overrides) -> QueryExpansionEngine:
    config = QueryExpansionConfig(
        enabled=overrides.get("enabled", True),
        stemming_enabled=overrides.get("stemming_enabled", True),
        synonyms_enabled=overrides.get("synonyms_enabled", True),
        llm_provider=overrides.get("llm_provider"),
        max_expansions=overrides.get("max_expansions", 5),
        llm_max_expansions=overrides.get("llm_max_expansions", 2),
        synonyms_path=None,
    )
    return QueryExpansionEngine(config)


def test_query_expansion_disabled():
    engine = build_engine(enabled=False)
    result = engine.expand("performance tuning")
    assert result.expanded_queries == []
    assert result.disabled_reason == "expansion_disabled"


def test_query_expansion_stemming_generates_variant():
    engine = build_engine(max_expansions=3)
    result = engine.expand("running services")
    assert result.expanded_queries
    assert any(step["step"] == "stemming" for step in result.applied_steps)


def test_query_expansion_synonym_swap():
    engine = build_engine(max_expansions=3)
    result = engine.expand("improve performance")
    assert any("latency" in variant for variant in result.expanded_queries)


def test_query_expansion_llm_mock(monkeypatch):
    engine = build_engine(llm_provider="mock", max_expansions=4, synonyms_enabled=False, stemming_enabled=False)
    result = engine.expand("reduce errors", context={"case": "llm"})
    assert any("explained" in variant for variant in result.expanded_queries)
    assert any(step["step"] == "llm_rewrite" for step in result.applied_steps)
