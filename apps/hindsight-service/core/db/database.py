import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection URL
# This should ideally come from environment variables for production
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres-service:5432/hindsight_db")

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
