import os
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool
from sqlalchemy.engine.url import make_url

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from core.db.models import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))

    # In test environments we sometimes need to bypass SQLAlchemy's URL handling
    # due to libpq/auth nuances. When ALEMBIC_TEST_USE_CREATOR=1, use a DBAPI
    # creator that builds a fresh psycopg2 connection directly from the URL.
    use_creator = os.getenv("ALEMBIC_TEST_USE_CREATOR") == "1"

    if use_creator:
        try:
            import psycopg2
        except Exception:
            psycopg2 = None

        if psycopg2 is None:
            # Fallback to regular engine if psycopg2 isn't available for some reason
            connectable = create_engine(url, poolclass=pool.NullPool)
        else:
            u = make_url(url)
            def _creator():
                return psycopg2.connect(
                    host=u.host,
                    port=u.port or 5432,
                    user=u.username,
                    password=u.password,
                    dbname=u.database,
                )
            connectable = create_engine("postgresql+psycopg2://", poolclass=pool.NullPool, creator=_creator)
    else:
        connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
