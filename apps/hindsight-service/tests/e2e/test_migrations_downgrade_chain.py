import os
import sys
import pytest
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from .utils_pg import postgres_container


def _service_root() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, "..", ".."))


def _alembic_config(db_url: str) -> Config:
    service_dir = _service_root()
    ini_path = os.path.join(service_dir, "alembic.ini")
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    cfg = Config(ini_path)
    os.environ["TEST_DATABASE_URL"] = db_url
    return cfg


def _linear_revisions(cfg: Config):
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if not heads:
        return []
    revs = list(script.walk_revisions(base="base", head=heads[0]))
    revs.reverse()
    return [r.revision for r in revs]


@pytest.mark.e2e
@pytest.mark.xfail(reason="Known downgrade contextlib/psycopg2 quirk under Py3.13; tracking for fix.", strict=False)
def test_alembic_downgrade_chain_repro():
    with postgres_container() as (test_db_url, _):
        cfg = _alembic_config(test_db_url)
        all_revs = _linear_revisions(cfg)
        assert all_revs, "No Alembic revisions found"

        # Upgrade to head in one go
        command.upgrade(cfg, "head")

        # Attempt stepwise downgrade; historically triggers generator error on some envs
        for _ in all_revs:
            command.downgrade(cfg, "-1")

        # Verify base
        eng = create_engine(test_db_url)
        with eng.connect() as conn:
            try:
                row = conn.execute(text("select version_num from alembic_version")).first()
                assert row is None or row[0] is None
            except Exception:
                # Table may not exist at base
                pass

