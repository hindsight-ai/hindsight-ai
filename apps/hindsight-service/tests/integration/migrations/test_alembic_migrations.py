from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from tests.e2e.utils_pg import postgres_container


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(os.getenv("SKIP_ALEMBIC_FIXTURES") == "1", reason="SKIP_ALEMBIC_FIXTURES=1")
def test_alembic_upgrade_and_downgrade_cycle() -> None:
    """Spin up a pgvector Postgres, upgrade to head, downgrade to base, and upgrade back."""
    service_root = Path(__file__).resolve().parents[3]
    ini_path = service_root / "alembic.ini"
    script_location = service_root / "migrations"

    with postgres_container() as (db_url, _name):
        cfg = Config(str(ini_path))
        cfg.set_main_option("sqlalchemy.url", db_url)
        cfg.set_main_option("script_location", str(script_location))

        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
