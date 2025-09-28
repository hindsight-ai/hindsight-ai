from types import SimpleNamespace
import uuid

from core.db import crud
from core.services.query_expansion import QueryExpansionResult


class DummyEngine:
    def __init__(self, expansions):
        self._expansions = expansions

    def expand(self, query, context):  # pylint: disable=unused-argument
        return QueryExpansionResult(original_query=query, expanded_queries=self._expansions, applied_steps=[{"step": "synonym"}])


def test_execute_with_query_expansion_merges_results(monkeypatch):
    expanded_id = uuid.uuid4()
    expanded_result = SimpleNamespace(id=expanded_id, search_score=0.9, search_type="fulltext", rank_explanation="synonym")

    engine = DummyEngine(["performance"])
    monkeypatch.setattr(crud, "get_query_expansion_engine", lambda: engine)

    def runner(query):
        if query == "performance":
            return [expanded_result], {"total_search_time_ms": 5.0, "search_type": "fulltext"}
        return [], {"total_search_time_ms": 1.0, "search_type": "fulltext"}

    results, metadata = crud._execute_with_query_expansion(  # pylint: disable=protected-access
        base_query="speed",
        limit=5,
        context={"search_type": "fulltext"},
        runner=runner,
        search_label="fulltext",
    )

    assert results == [expanded_result]
    assert metadata["expansion"]["expanded_queries"] == ["performance"]
    assert metadata["search_type"] == "fulltext_expanded"
    assert metadata["combined_results_count"] == 1
    assert metadata["total_search_time_ms"] == 6.0


def test_search_memory_blocks_hybrid_uses_expansion(monkeypatch):
    expanded_id = uuid.uuid4()
    expanded_result = SimpleNamespace(
        id=expanded_id,
        search_score=0.8,
        search_type="hybrid",
        rank_explanation="expanded",
    )

    engine = DummyEngine(["performance"])
    monkeypatch.setattr(crud, "get_query_expansion_engine", lambda: engine)

    calls = []

    class FakeService:
        def search_memory_blocks_hybrid(self, **kwargs):  # pylint: disable=unused-argument
            query = kwargs["query"]
            calls.append(query)
            if query == "performance":
                return [expanded_result], {"total_search_time_ms": 5.0, "search_type": "hybrid"}
            return [], {"total_search_time_ms": 1.0, "search_type": "hybrid"}

    monkeypatch.setattr("core.search.get_search_service", lambda: FakeService())

    results, metadata = crud.search_memory_blocks_hybrid(
        db=SimpleNamespace(),
        query="speed",
        agent_id=None,
        conversation_id=None,
        limit=5,
        fulltext_weight=0.7,
        semantic_weight=0.3,
        min_combined_score=0.1,
        include_archived=False,
        current_user=None,
    )

    assert calls == ["speed", "performance"]
    assert results == [expanded_result]
    assert metadata["expansion"]["expanded_queries"] == ["performance"]
    assert metadata["search_type"].endswith("_expanded")
