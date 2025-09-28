import pytest


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    """Override migration fixture for pure unit tests that do not touch the database."""
    yield
