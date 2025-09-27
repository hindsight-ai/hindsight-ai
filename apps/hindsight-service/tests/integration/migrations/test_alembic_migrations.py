from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from tests.e2e.utils_pg import postgres_container


def _make_alembic_config(database_url: str) -> Config:
    """Return an Alembic config pointing at the service migrations."""
    service_root = Path(__file__).resolve().parents[3]
    cfg = Config(str(service_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(service_root / "migrations"))
    return cfg


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(os.getenv("SKIP_ALEMBIC_FIXTURES") == "1", reason="SKIP_ALEMBIC_FIXTURES=1")
def test_alembic_upgrade_and_downgrade_cycle() -> None:
    """Ensure migrations upgrade from base→head and cleanly downgrade back to base."""
    with postgres_container() as (database_url, _name):
        cfg = _make_alembic_config(database_url)

        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
