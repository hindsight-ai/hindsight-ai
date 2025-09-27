from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


def _make_alembic_config(database_url: str) -> Config:
    """Return an Alembic config pointing at the service migrations."""
    service_root = Path(__file__).resolve().parents[3]
    cfg = Config(str(service_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(service_root / "migrations"))
    return cfg


@pytest.mark.integration
@pytest.mark.slow
def test_alembic_upgrade_and_downgrade_cycle(_test_postgres: str) -> None:
    """Ensure migrations upgrade from base→head and cleanly downgrade back to base."""
    cfg = _make_alembic_config(_test_postgres)

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
