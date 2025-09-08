import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection URL
# This should ideally come from environment variables for production
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/hindsight_db")

# Lightweight test override: if PYTEST_CURRENT_TEST is set and no explicit DATABASE_URL provided, use in-memory sqlite
if "PYTEST_CURRENT_TEST" in os.environ and os.getenv("DATABASE_URL") is None:
    DATABASE_URL = "sqlite+pysqlite:///:memory:"
    _sqlite_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    _sqlite_kwargs = {}

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, **_sqlite_kwargs)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session_local():
    """Return a sessionmaker factory (used by background worker threads)."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
