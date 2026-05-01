"""
Abstract base class for all search strategies.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy.orm import Session

from core.db import schemas

if TYPE_CHECKING:
    from core.api.deps import CurrentUserContext


class SearchStrategy(ABC):
    """Abstract interface that every concrete search strategy must implement."""

    @abstractmethod
    def search(
        self,
        db: Session,
        query: str,
        *,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        include_archived: bool = False,
        current_user: Optional["CurrentUserContext"] = None,
        **kwargs: Any,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """Execute the search and return (results, metadata)."""
        ...
