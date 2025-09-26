import math
from types import SimpleNamespace

import pytest

from core.db import types as db_types


class DummyDialect:
    def __init__(self, name="postgresql"):
        self.name = name
        self.calls = []

    def type_descriptor(self, value):
        self.calls.append(value)
        return value


def test_embedding_vector_prefers_safe_pgvector(monkeypatch):
    captured = {}

    class DummyVector:
        def __init__(self, dim=None):
            captured["dim"] = dim

    dialect = DummyDialect()
    monkeypatch.setattr(db_types, "_SafePGVector", DummyVector)
    monkeypatch.setattr(db_types, "Vector", object())  # ensure fallback is unused

    embedding_type = db_types.EmbeddingVector(dimension=7)
    result = embedding_type.load_dialect_impl(dialect)

    assert isinstance(result, DummyVector)
    assert captured["dim"] == 7
    assert dialect.calls[0] is result


def test_embedding_vector_falls_back_without_pgvector(monkeypatch):
    dialect = DummyDialect()
    monkeypatch.setattr(db_types, "_SafePGVector", None)
    monkeypatch.setattr(db_types, "Vector", None)

    embedding_type = db_types.EmbeddingVector()
    descriptor = embedding_type.load_dialect_impl(dialect)

    # Without pgvector we should use JSONB / JSON descriptors
    assert isinstance(descriptor, db_types.postgresql.JSONB)
    assert descriptor.none_as_null is True


def test_embedding_vector_process_result_handles_strings(monkeypatch):
    dialect = SimpleNamespace(name="postgresql")
    monkeypatch.setattr(db_types, "Vector", None)

    embedding_type = db_types.EmbeddingVector()

    list_value = embedding_type.process_result_value([1, "2", 3.0], dialect)
    assert list_value == [1.0, 2.0, 3.0]

    json_value = embedding_type.process_result_value('[1, 2, 3]', dialect)
    assert json_value == [1.0, 2.0, 3.0]

    brace_value = embedding_type.process_result_value('{4,5,6}', dialect)
    assert brace_value == [4.0, 5.0, 6.0]


def test_embedding_vector_bind_param_validates_dimension(monkeypatch):
    dialect = SimpleNamespace(name="postgresql")
    monkeypatch.setattr(db_types, "Vector", object())

    embedding_type = db_types.EmbeddingVector(dimension=2)
    with pytest.raises(ValueError):
        embedding_type.process_bind_param([1, 2, 3], dialect)

    vector = embedding_type.process_bind_param([0.1, math.pi], SimpleNamespace(name="sqlite"))
    assert vector == [0.1, math.pi]
