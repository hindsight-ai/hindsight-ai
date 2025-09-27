from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.services.search_service import SearchService
from core.services import search_service


@pytest.fixture(scope="session")
def _test_postgres():
    return "postgresql://mock:mock@localhost/mock"


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    yield


@pytest.fixture(autouse=True)
def db_session():
    yield None


def _fake_basic_results(*args, **kwargs):
    return (["fallback"], {"search_type": "basic"})


def test_semantic_search_falls_back_when_embedding_disabled(monkeypatch):
    service = SearchService()
    monkeypatch.setattr(service, "_basic_search_fallback", MagicMock(side_effect=_fake_basic_results))
    fake_embed_service = SimpleNamespace(is_enabled=False)
    monkeypatch.setattr(search_service, "get_embedding_service", lambda: fake_embed_service)

    results, meta = service.search_memory_blocks_semantic(db=SimpleNamespace(), query="hello")

    assert results == ["fallback"]
    assert meta["search_type"] == "semantic_fallback"
    assert meta["fallback_reason"] == "embedding_provider_disabled"


def test_semantic_search_falls_back_when_embedding_missing(monkeypatch):
    service = SearchService()
    monkeypatch.setattr(service, "_basic_search_fallback", MagicMock(side_effect=_fake_basic_results))

    fake_embed_service = SimpleNamespace(is_enabled=True, embed_text=lambda text: None)
    monkeypatch.setattr(search_service, "get_embedding_service", lambda: fake_embed_service)

    results, meta = service.search_memory_blocks_semantic(db=SimpleNamespace(), query="hello")

    assert results == ["fallback"]
    assert meta["fallback_reason"] == "query_embedding_unavailable"


def test_semantic_search_falls_back_for_non_postgres(monkeypatch):
    service = SearchService()
    monkeypatch.setattr(service, "_basic_search_fallback", MagicMock(side_effect=_fake_basic_results))

    fake_embed_service = SimpleNamespace(is_enabled=True, embed_text=lambda text: [0.1, 0.2])
    monkeypatch.setattr(search_service, "get_embedding_service", lambda: fake_embed_service)

    fake_db = SimpleNamespace(bind=SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))

    results, meta = service.search_memory_blocks_semantic(db=fake_db, query="hello", current_user=None)

    assert results == ["fallback"]
    assert meta["fallback_reason"].startswith("dialect_")


def test_semantic_search_handles_query_failure(monkeypatch):
    service = SearchService()
    monkeypatch.setattr(service, "_basic_search_fallback", MagicMock(side_effect=_fake_basic_results))

    fake_embed_service = SimpleNamespace(is_enabled=True, embed_text=lambda text: [0.1, 0.2])
    monkeypatch.setattr(search_service, "get_embedding_service", lambda: fake_embed_service)

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            raise RuntimeError("boom")

    fake_db = SimpleNamespace(
        bind=SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        query=lambda *args, **kwargs: FakeQuery(),
    )

    # Ensure SQLAlchemy cast is a no-op to simplify the test
    monkeypatch.setattr(search_service, "cast", lambda expr, typ: expr)

    results, meta = service.search_memory_blocks_semantic(db=fake_db, query="hello")

    assert results == ["fallback"]
    assert meta["fallback_reason"] == "semantic_query_error"


def test_semantic_search_interprets_threshold(monkeypatch):
    service = SearchService()

    # bypass embed service to reach threshold logic
    fake_embed_service = SimpleNamespace(is_enabled=True, embed_text=lambda text: [0.1, 0.2])
    monkeypatch.setattr(search_service, "get_embedding_service", lambda: fake_embed_service)

    # build a minimal in-memory setup that returns a single result with distance 0.2
    class FakeQuery:
        def __init__(self):
            self._distance = 0.2

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            fake_memory = SimpleNamespace(
                agent_id=None,
                conversation_id=None,
                content="",
                errors=None,
                lessons_learned=None,
                metadata_col=None,
                feedback_score=0,
                retrieval_count=0,
                archived=False,
                archived_at=None,
                visibility_scope="public",
                owner_user_id=None,
                organization_id=None,
                content_embedding=None,
                id="fake",
                timestamp=None,
                created_at=None,
                updated_at=None,
                keywords=[],
            )
            return [(fake_memory, self._distance)]

    fake_db = SimpleNamespace(
        bind=SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        query=lambda *args, **kwargs: FakeQuery(),
    )

    monkeypatch.setattr(search_service, "cast", lambda expr, typ: expr)
    monkeypatch.setattr(search_service, "_create_memory_block_with_score", lambda block, score, search_type, explanation, extras: {"score": score, "extras": extras})

    results, meta = service.search_memory_blocks_semantic(db=fake_db, query="hello", similarity_threshold=0.7)

    assert results[0]["score"] == pytest.approx(0.8)
    assert meta["semantic_results_count"] == 1
    assert meta["search_type"] == "semantic"
