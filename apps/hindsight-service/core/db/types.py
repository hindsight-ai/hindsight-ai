"""Custom SQLAlchemy types used by the persistence layer."""
from __future__ import annotations

import json
from typing import Iterable, List, Optional

from sqlalchemy.dialects import postgresql
from sqlalchemy.types import JSON, TypeDecorator

try:  # pragma: no cover - optional dependency
    from pgvector.sqlalchemy import Vector  # type: ignore
    from pgvector.sqlalchemy.vector import VECTOR as PGVector  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Vector = None  # type: ignore
    PGVector = None  # type: ignore


if PGVector is not None:  # pragma: no cover - optional dependency
    class _SafePGVector(PGVector):
        """PGVector variant resilient to psycopg returning Python sequences."""

        def result_processor(self, dialect, coltype):  # type: ignore[override]
            base_processor = super().result_processor(dialect, coltype)

            def process(value):
                if isinstance(value, (list, tuple)):
                    return [float(v) for v in value]
                return base_processor(value)

            return process

else:  # pragma: no cover - optional dependency
    _SafePGVector = None  # type: ignore


class EmbeddingVector(TypeDecorator[List[float]]):
    """Store embedding vectors with pgvector when available.

    Falls back to JSON storage on dialects that do not support pgvector
    (e.g. SQLite during unit tests).
    """

    cache_ok = True
    impl = JSON

    def __init__(self, dimension: Optional[int] = None) -> None:
        super().__init__()
        self._dimension = dimension

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            dim = self._dimension
            if _SafePGVector is not None:
                try:
                    return dialect.type_descriptor(_SafePGVector(dim))  # type: ignore[arg-type]
                except TypeError:
                    return dialect.type_descriptor(_SafePGVector())  # type: ignore[call-arg]
            if Vector is not None:
                try:
                    return dialect.type_descriptor(Vector(dim))  # type: ignore[arg-type]
                except TypeError:
                    return dialect.type_descriptor(Vector())  # type: ignore[call-arg]
            return dialect.type_descriptor(postgresql.JSONB(none_as_null=True))
        return dialect.type_descriptor(JSON(none_as_null=True))

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, tuple):
            value = list(value)
        if not isinstance(value, Iterable):
            raise TypeError(
                f"EmbeddingVector expects an iterable of floats, got {type(value)!r}"
            )
        vector = [float(v) for v in value]
        if dialect.name == "postgresql" and Vector is not None:
            # pgvector driver expects a plain python sequence
            if self._dimension and len(vector) != self._dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self._dimension}, got {len(vector)}"
                )
            return vector
        return vector

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        if dialect.name == "postgresql" and Vector is not None:
            try:
                return [float(v) for v in value]
            except TypeError:
                # Some drivers return str when pgvector extension missing; attempt to parse JSON
                pass
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [float(v) for v in parsed]
            except json.JSONDecodeError:
                # Fallback for Postgres array string format "{..}".
                stripped = value.strip("{}")
                if not stripped:
                    return []
                return [float(part) for part in stripped.split(",")]
        if isinstance(value, (list, tuple)):
            return [float(v) for v in value]
        if hasattr(value, "tolist"):
            return [float(v) for v in value.tolist()]
        return value

    def copy(self, **kwargs):  # type: ignore[override]
        return EmbeddingVector(dimension=self._dimension)
