import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from core.pruning.pruning_service import PruningService


class TestPruningService:
    """Test cases for the PruningService class aligned with current API."""

    def test_evaluate_memory_blocks_fallback_scoring(self):
        """When no LLM key is provided, fallback scoring is used."""
        service = PruningService()  # no LLM key => fallback

        memory_blocks = [
            {
                "id": str(uuid.uuid4()),
                "content": "Critical error encountered: Database connection failed",
                "retrieval_count": 10,
                "feedback_score": 0,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "content": "Everything worked fine, no issues encountered",
                "retrieval_count": 0,
                "feedback_score": 0,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=365)).isoformat(),
            },
        ]

        evaluated = service.evaluate_memory_blocks_with_llm(memory_blocks)
        assert isinstance(evaluated, list)
        assert len(evaluated) == 2
        for item in evaluated:
            assert "pruning_score" in item
            assert 1 <= item["pruning_score"] <= 100
            assert "pruning_rationale" in item

    def test_pruning_service_initialization(self):
        """Service stores provided LLM API key."""
        service = PruningService(llm_api_key="dummy-key")
        assert service.llm_api_key == "dummy-key"

    def test_generate_pruning_suggestions(self):
        """Generate pruning suggestions with mocked memory blocks and DB."""
        mock_db = Mock()
        service = PruningService()  # no LLM => fallback path

        # Prepare mock blocks in the dict format expected by evaluate method
        mock_memory_blocks = []
        for i in range(5):
            mock_memory_blocks.append(
                {
                    "id": str(uuid.uuid4()),
                    "content": f"Test memory block {i}",
                    "created_at": (datetime.now(timezone.utc) - timedelta(days=i * 30)).isoformat(),
                    "retrieval_count": i,
                    "feedback_score": 0,
                }
            )

        # Patch get_random_memory_blocks to avoid DB internals and SQL func calls
        with patch.object(PruningService, "get_random_memory_blocks", return_value=mock_memory_blocks):
            result = service.generate_pruning_suggestions(
                db=mock_db, batch_size=3, target_count=2
            )

        assert isinstance(result, dict)
        assert "suggestions" in result
        suggestions = result["suggestions"]
        assert isinstance(suggestions, list)
        # Should be limited by target_count
        assert len(suggestions) <= 2
        if suggestions:
            first = suggestions[0]
            assert "memory_block_id" in first
            assert "pruning_score" in first
            assert "content_preview" in first
