"""SQLite compilation shims for PostgreSQL-specific SQLAlchemy types.

This module installs lightweight compilers for JSONB and TSVECTOR when the
active dialect is SQLite so that declarative metadata can be created in test
runs that substitute an in-memory SQLite database. The goal is only to allow
`Base.metadata.create_all()` to succeed; no attempt is made to fully emulate
PostgreSQL JSONB or full-text search behavior.

Usage: Imported for side-effects by core.db.models.
"""
from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.sqltypes import JSON

# Only register compilers if SQLAlchemy is asked to compile for SQLite.
# These functions are ignored for other dialects.

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):  # pragma: no cover - trivial
    # Map JSONB to a generic JSON (stored as TEXT) for SQLite. This loses
    # JSONB operators and indexing capabilities but preserves storage so
    # tests can insert and retrieve simple values.
    return "JSON"

@compiles(TSVECTOR, "sqlite")
def _compile_tsvector_sqlite(element, compiler, **kw):  # pragma: no cover - trivial
    # Represent TSVECTOR as TEXT in SQLite. Full-text features won't work;
    # tests using SQLite should not rely on PostgreSQL full-text search.
    return "TEXT"
