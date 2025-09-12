"""
App assembly entry point.

Re-exports the FastAPI `app` from `core.api.main` to keep compatibility while
we gradually refactor routers into dedicated modules.
"""

from core.api.main import app  # noqa: F401

