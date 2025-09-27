from __future__ import annotations

import runpy
from pathlib import Path

MODULE_GLOBALS = runpy.run_path(Path(__file__).resolve().parents[2] / "scripts" / "backfill_embeddings.py")
BACKFILL = MODULE_GLOBALS["backfill"]
MAIN = MODULE_GLOBALS["main"]


class DummySession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _patch(module_globals, **overrides):
    for key, value in overrides.items():
        module_globals[key] = value


def test_backfill_dry_run(monkeypatch, capsys):
    session = DummySession()
    _patch(
        BACKFILL.__globals__,
        SessionLocal=lambda: session,
        count_missing=lambda _: 7,
    )

    exit_code = MAIN(["--dry-run"])

    assert exit_code == 0
    assert session.closed is True
    out = capsys.readouterr().out
    assert "7 memory blocks" in out


def test_backfill_disabled_provider(monkeypatch, capsys):
    session = DummySession()

    class DisabledService:
        is_enabled = False

    _patch(
        BACKFILL.__globals__,
        SessionLocal=lambda: session,
        count_missing=lambda _: 3,
        get_embedding_service=lambda: DisabledService(),
    )

    exit_code = MAIN([])

    assert exit_code == 1
    assert session.closed is True
    err = capsys.readouterr().err
    assert "Embedding provider is disabled" in err


def test_backfill_runs(monkeypatch, capsys):
    session = DummySession()

    class EnabledService:
        is_enabled = True

        def backfill_missing_embeddings(self, sess, batch_size):
            assert sess is session
            assert batch_size == 50
            return 4

    _patch(
        BACKFILL.__globals__,
        SessionLocal=lambda: session,
        count_missing=lambda _: 5,
        get_embedding_service=lambda: EnabledService(),
    )

    exit_code = MAIN(["--batch-size", "50"])

    assert exit_code == 0
    assert session.closed is True
    out = capsys.readouterr().out
    assert "Backfilled embeddings for 4" in out
