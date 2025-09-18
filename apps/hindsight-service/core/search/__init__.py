"""
Search module compatibility shim.

New code should import from `core.services.search_service`.
This module re-exports the service for backward compatibility.
"""

from core.services.search_service import SearchService, get_search_service  # type: ignore

__all__ = ["SearchService", "get_search_service"]
