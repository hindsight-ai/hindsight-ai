import json
import os
import runpy
import sys
import uuid
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from core.workers import consolidation_worker as worker


def _install_fake_google(monkeypatch, client_factory):
    """Inject a stub google.genai module returning the provided client."""
    fake_google = ModuleType("google")
    fake_genai = ModuleType("google.genai")
    fake_genai.Client = client_factory
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)


def test_safe_group_id_handles_errors():
    class Bad:
        def get(self, key, default=None):
            raise RuntimeError("boom")

    assert worker._safe_group_id(Bad()) == "unknown"
    assert worker._safe_group_id({"group_id": uuid.uuid4()}) != "unknown"


def test_fetch_memory_blocks_success(monkeypatch):
    class Block:
        def __init__(self, value):
            self.id = value
            self.content = f"content-{value}"

    blocks = [Block("a"), Block("b")]
    monkeypatch.setattr(worker, "get_all_memory_blocks", lambda db, skip, limit: blocks)

    db = MagicMock()
    result = worker.fetch_memory_blocks(db, offset=0, limit=5)

    assert [b.__dict__ for b in blocks] == result


def test_fetch_memory_blocks_handles_exception(monkeypatch):
    monkeypatch.setattr(worker, "get_all_memory_blocks", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    db = MagicMock()

    result = worker.fetch_memory_blocks(db, offset=0, limit=5)

    assert result == []


def test_analyze_duplicates_with_llm_requires_model_name(monkeypatch):
    fallback_groups = [{"group_id": "grp", "memory_ids": ["1"]}]
    monkeypatch.setattr(worker, "analyze_duplicates_with_fallback", lambda blocks: fallback_groups)

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text="{}"))

    _install_fake_google(monkeypatch, FakeClient)
    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)

    result = worker.analyze_duplicates_with_llm([{"id": "1", "content": "text", "lessons_learned": ""}], llm_api_key="key")

    assert result == fallback_groups


def test_analyze_duplicates_with_llm_trims_long_responses(monkeypatch):
    block_a = {"id": uuid.uuid4(), "content": "short", "lessons_learned": "alpha", "keywords": []}
    block_b = {"id": uuid.uuid4(), "content": "this is much longer", "lessons_learned": "beta lessons", "keywords": []}
    memory_blocks = [block_a, block_b]

    fallback_groups = [{"group_id": "grp", "memory_ids": [str(block_a["id"]), str(block_b["id"])]}]
    monkeypatch.setattr(worker, "analyze_duplicates_with_fallback", lambda blocks: fallback_groups)

    def generate_content(**kwargs):
        payload = {
            "suggested_content": "this is much longer than allowed",  # longer than block_b
            "suggested_lessons_learned": "beta lessons extended",       # longer than block_b lessons
            "suggested_keywords": ["kw"]
        }
        return SimpleNamespace(text=json.dumps(payload))

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = SimpleNamespace(generate_content=generate_content)

    _install_fake_google(monkeypatch, FakeClient)
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")

    result = worker.analyze_duplicates_with_llm(memory_blocks, llm_api_key="key")

    assert len(result) == 1
    group = result[0]
    assert group["suggested_content"] == "this is much longer"
    assert group["suggested_lessons_learned"] == "beta lessons"
    assert group["suggested_keywords"] == ["kw"]


def test_analyze_duplicates_with_llm_preserves_short_response(monkeypatch):
    block = {"id": uuid.uuid4(), "content": "abc", "lessons_learned": "xyz", "keywords": []}
    memory_blocks = [block]
    fallback_groups = [{"group_id": "grp", "memory_ids": [str(block["id"])], "suggested_content": ""}]
    monkeypatch.setattr(worker, "analyze_duplicates_with_fallback", lambda blocks: fallback_groups)

    class FakeClient:
        def __init__(self, api_key):
            self.models = SimpleNamespace(
                generate_content=lambda **kwargs: SimpleNamespace(
                    text=json.dumps(
                        {
                            "suggested_content": "abc",
                            "suggested_lessons_learned": "xyz",
                            "suggested_keywords": ["kw"],
                        }
                    )
                )
            )

    _install_fake_google(monkeypatch, FakeClient)
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")

    result = worker.analyze_duplicates_with_llm(memory_blocks, llm_api_key="key")

    assert result[0]["suggested_content"] == "abc"
    assert result[0]["suggested_lessons_learned"] == "xyz"
    assert result[0]["suggested_keywords"] == ["kw"]


def test_analyze_duplicates_with_llm_returns_group_on_bad_json(monkeypatch):
    block = {"id": uuid.uuid4(), "content": "data", "lessons_learned": "info", "keywords": []}
    fallback_groups = [{"group_id": "grp", "memory_ids": [str(block["id"])], "extra": True}]
    monkeypatch.setattr(worker, "analyze_duplicates_with_fallback", lambda blocks: fallback_groups)

    class FakeClient:
        def __init__(self, api_key):
            self.models = SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text="{invalid"))

    _install_fake_google(monkeypatch, FakeClient)
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")

    result = worker.analyze_duplicates_with_llm([block], llm_api_key="key")

    assert result == fallback_groups


def test_analyze_duplicates_with_llm_returns_fallback_on_model_error(monkeypatch):
    block = {"id": uuid.uuid4(), "content": "data", "lessons_learned": "info", "keywords": []}
    fallback_groups = [{"group_id": "grp", "memory_ids": [str(block["id"])], "from_fallback": True}]
    monkeypatch.setattr(worker, "analyze_duplicates_with_fallback", lambda blocks: fallback_groups)

    def _boom(**kwargs):
        raise RuntimeError("model failure")

    class FakeClient:
        def __init__(self, api_key):
            self.models = SimpleNamespace(generate_content=_boom)

    _install_fake_google(monkeypatch, FakeClient)
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")

    result = worker.analyze_duplicates_with_llm([block], llm_api_key="key")

    assert result == fallback_groups


def test_store_consolidation_suggestions_creates_entries(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    created_payloads = []

    def fake_create(db_session, schema):
        created_payloads.append(schema)

    monkeypatch.setattr(worker, "create_consolidation_suggestion", fake_create)

    # Replace the schema constructor with a simple recorder so we can inspect values
    import core.db.schemas as schemas

    class FakeSchema:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(schemas, "ConsolidationSuggestionCreate", FakeSchema)

    invalid_uuid_group = {
        "group_id": "not-a-uuid",
        "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        "suggested_content": "c",
        "suggested_lessons_learned": "l",
        "suggested_keywords": ["kw"],
    }

    created = worker.store_consolidation_suggestions(db, [invalid_uuid_group])

    assert created == 1
    assert db.commit.called
    assert len(created_payloads) == 1
    payload = created_payloads[0].kwargs
    # New UUID generated and memory IDs coerced to strings
    assert isinstance(payload["group_id"], uuid.UUID)
    assert payload["original_memory_ids"] == sorted(invalid_uuid_group["memory_ids"])
    assert payload["suggested_keywords"] == ["kw"]


def test_store_consolidation_suggestions_skips_overlap(monkeypatch):
    db = MagicMock()
    existing = MagicMock()
    overlap_id = str(uuid.uuid4())
    existing.original_memory_ids = [overlap_id]
    db.query.return_value.filter.return_value.all.return_value = [existing]

    monkeypatch.setattr(worker, "create_consolidation_suggestion", MagicMock())

    group = {
        "group_id": str(uuid.uuid4()),
        "memory_ids": [overlap_id, str(uuid.uuid4())],
        "suggested_content": "c",
        "suggested_lessons_learned": "l",
        "suggested_keywords": [],
    }

    created = worker.store_consolidation_suggestions(db, [group])

    assert created == 0
    worker.create_consolidation_suggestion.assert_not_called()
    assert db.commit.called


def test_store_consolidation_suggestions_skips_when_missing_fields(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    monkeypatch.setattr(worker, "create_consolidation_suggestion", MagicMock())

    group = {
        "group_id": str(uuid.uuid4()),
        "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        "suggested_content": "",  # missing content
        "suggested_lessons_learned": "",  # missing lessons
        "suggested_keywords": [],
    }

    created = worker.store_consolidation_suggestions(db, [group])

    assert created == 0
    worker.create_consolidation_suggestion.assert_not_called()
    assert db.commit.called


def test_store_consolidation_suggestions_handles_no_overlap(monkeypatch):
    db = MagicMock()
    existing = MagicMock()
    existing.original_memory_ids = [str(uuid.uuid4())]
    db.query.return_value.filter.return_value.all.return_value = [existing]

    import core.db.schemas as schemas

    class FakeSchema:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(schemas, "ConsolidationSuggestionCreate", FakeSchema)

    create_mock = MagicMock()
    monkeypatch.setattr(worker, "create_consolidation_suggestion", create_mock)

    group = {
        "group_id": str(uuid.uuid4()),
        "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        "suggested_content": "c",
        "suggested_lessons_learned": "l",
        "suggested_keywords": [],
    }

    created = worker.store_consolidation_suggestions(db, [group])

    assert created == 1
    create_mock.assert_called_once()
    assert db.commit.called


def test_store_consolidation_suggestions_handles_create_error(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    def fake_create(db_session, schema):
        raise ValueError("db error")

    monkeypatch.setattr(worker, "create_consolidation_suggestion", fake_create)

    import core.db.schemas as schemas

    class FakeSchema:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(schemas, "ConsolidationSuggestionCreate", FakeSchema)

    group = {
        "group_id": str(uuid.uuid4()),
        "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        "suggested_content": "c",
        "suggested_lessons_learned": "l",
        "suggested_keywords": [],
    }

    created = worker.store_consolidation_suggestions(db, [group])

    assert created == 0
    assert db.commit.called


def test_store_consolidation_suggestions_handles_query_error(monkeypatch):
    db = MagicMock()
    db.query.side_effect = RuntimeError("query failed")

    monkeypatch.setattr(worker, "create_consolidation_suggestion", MagicMock())

    import core.db.schemas as schemas

    class FakeSchema:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(schemas, "ConsolidationSuggestionCreate", FakeSchema)

    group = {
        "group_id": str(uuid.uuid4()),
        "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        "suggested_content": "c",
        "suggested_lessons_learned": "l",
        "suggested_keywords": [],
    }

    created = worker.store_consolidation_suggestions(db, [group])

    assert created == 0
    assert db.commit.called


def test_run_consolidation_analysis_processes_batches(monkeypatch):
    db = MagicMock()
    db.close = MagicMock()

    def fake_get_db():
        yield db

    monkeypatch.setattr(worker, "get_db", fake_get_db)

    first_batch = [{"id": i} for i in range(worker.BATCH_SIZE)]
    fetch_mock = MagicMock(side_effect=[first_batch, []])
    monkeypatch.setattr(worker, "fetch_memory_blocks", fetch_mock)

    analyze_mock = MagicMock(return_value=[
        {
            "group_id": "g",
            "memory_ids": ["1"],
            "suggested_content": "c",
            "suggested_lessons_learned": "l",
            "suggested_keywords": [],
        }
    ])
    store_mock = MagicMock(return_value=2)
    monkeypatch.setattr(worker, "analyze_duplicates_with_llm", analyze_mock)
    monkeypatch.setattr(worker, "store_consolidation_suggestions", store_mock)

    worker.run_consolidation_analysis("key")

    assert fetch_mock.call_args_list == [
        call(db, 0, worker.BATCH_SIZE),
        call(db, worker.BATCH_SIZE, worker.BATCH_SIZE),
    ]
    store_mock.assert_called_once()
    analyze_mock.assert_called_once()
    db.close.assert_called_once()


def test_run_consolidation_analysis_handles_exception(monkeypatch):
    db = MagicMock()
    db.close = MagicMock()

    def fake_get_db():
        yield db

    monkeypatch.setattr(worker, "get_db", fake_get_db)

    def fake_fetch(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(worker, "fetch_memory_blocks", fake_fetch)
    monkeypatch.setattr(worker, "analyze_duplicates_with_llm", MagicMock())
    monkeypatch.setattr(worker, "store_consolidation_suggestions", MagicMock())

    worker.run_consolidation_analysis("key")

    assert db.close.called


def test_fetch_memory_blocks_returns_empty_batch(monkeypatch):
    monkeypatch.setattr(worker, "get_all_memory_blocks", lambda *args, **kwargs: [])
    result = worker.fetch_memory_blocks(MagicMock(), offset=0, limit=10)
    assert result == []


def test_analyze_duplicates_with_llm_no_memory_blocks():
    assert worker.analyze_duplicates_with_llm([], llm_api_key="key") == []


def test_analyze_duplicates_with_llm_no_duplicate_groups(monkeypatch):
    monkeypatch.setattr(worker, "analyze_duplicates_with_fallback", lambda blocks: [])
    result = worker.analyze_duplicates_with_llm(
        [{"id": uuid.uuid4(), "content": "note", "lessons_learned": ""}],
        llm_api_key="key",
    )
    assert result == []


def test_analyze_duplicates_with_fallback_small_input():
    blocks = [{"id": uuid.uuid4(), "content": "only one", "lessons_learned": ""}]
    assert worker.analyze_duplicates_with_fallback(blocks) == []


def test_analyze_duplicates_with_fallback_detects_group():
    a_id = uuid.uuid4()
    b_id = uuid.uuid4()
    blocks = [
        {"id": a_id, "content": "shared text", "lessons_learned": ""},
        {"id": b_id, "content": "shared text", "lessons_learned": ""},
        {"id": uuid.uuid4(), "content": "different", "lessons_learned": ""},
    ]
    groups = worker.analyze_duplicates_with_fallback(blocks)
    assert any({str(a_id), str(b_id)}.issubset(set(group["memory_ids"])) for group in groups)


def test_store_consolidation_suggestions_handles_value_error(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    import core.db.schemas as schemas

    monkeypatch.setattr(schemas, "ConsolidationSuggestionCreate", lambda **kwargs: kwargs)
    monkeypatch.setattr(worker, "create_consolidation_suggestion", MagicMock())

    class BadGroup(dict):
        def get(self, key, default=None):
            if key == "suggested_keywords":
                raise ValueError("bad kw")
            if key == "group_id" and default is None:
                raise ValueError("bad id")
            return super().get(key, default)

    bad_group = BadGroup(
        {
            "group_id": str(uuid.uuid4()),
            "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "suggested_content": "c",
            "suggested_lessons_learned": "l",
            "suggested_keywords": [],
        }
    )

    created = worker.store_consolidation_suggestions(db, [bad_group])

    assert created == 0
    assert db.commit.called


def test_run_consolidation_analysis_breaks_on_short_batch(monkeypatch):
    db = MagicMock()
    db.close = MagicMock()

    def fake_get_db():
        yield db

    monkeypatch.setattr(worker, "get_db", fake_get_db)
    monkeypatch.setattr(worker, "BATCH_SIZE", 5)

    fetch_mock = MagicMock(return_value=[{"id": uuid.uuid4()}])
    monkeypatch.setattr(worker, "fetch_memory_blocks", fetch_mock)
    monkeypatch.setattr(worker, "analyze_duplicates_with_llm", MagicMock(return_value=[]))
    monkeypatch.setattr(worker, "store_consolidation_suggestions", MagicMock(return_value=0))

    worker.run_consolidation_analysis("key")

    fetch_mock.assert_called_once()
    db.close.assert_called_once()


def test_main_block_executes_without_db(monkeypatch, tmp_path):
    module_path = worker.__file__

    fake_db = MagicMock()
    fake_db.close = MagicMock()

    def fake_get_db():
        yield fake_db

    fake_crud = ModuleType("core.db.crud")
    fake_crud.get_all_memory_blocks = lambda *args, **kwargs: []
    fake_crud.create_consolidation_suggestion = lambda *args, **kwargs: None

    fake_database = ModuleType("core.db.database")
    fake_database.get_db = fake_get_db

    monkeypatch.setitem(sys.modules, "core.db.crud", fake_crud)
    monkeypatch.setitem(sys.modules, "core.db.database", fake_database)

    monkeypatch.chdir(tmp_path)

    monkeypatch.setenv("LLM_API_KEY", "")

    runpy.run_path(module_path, run_name="__main__")
    assert fake_db.close.called

    # Run again with an API key set to cover alternate branch
    fake_db2 = MagicMock()
    fake_db2.close = MagicMock()

    def fake_get_db2():
        yield fake_db2

    fake_database.get_db = fake_get_db2
    monkeypatch.setenv("LLM_API_KEY", "api-key")

    runpy.run_path(module_path, run_name="__main__")

    assert fake_db2.close.called
