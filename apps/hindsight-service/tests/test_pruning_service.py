import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from core.pruning.pruning_service import PruningService, calculate_usefulness_score
from core.db.models import MemoryBlock

class TestPruningService:
    """Test cases for the PruningService class."""

    def test_calculate_usefulness_score_basic(self):
        """Test basic usefulness score calculation."""
        # Test memory block with high criticality and information value
        memory_block = Mock()
        memory_block.content = "Critical error encountered: Database connection failed"
        memory_block.retrieval_count = 10
        memory_block.created_at = datetime.now() - timedelta(days=30)
        memory_block.archived = False
        memory_block.consolidation_status = "none"
        
        # Mock LLM response
        mock_llm_response = {
            "criticality": 8,
            "information_value": 7,
            "redundancy": 2,
            "temporal_relevance": 6
        }
        
        with patch('core.pruning.pruning_service.call_llm_with_prompt', return_value=mock_llm_response):
            score = calculate_usefulness_score(memory_block)
            assert isinstance(score, (int, float))
            assert 0 <= score <= 10

    def test_calculate_usefulness_score_archived_block(self):
        """Test that archived blocks get score 0."""
        memory_block = Mock()
        memory_block.archived = True
        
        score = calculate_usefulness_score(memory_block)
        assert score == 0

    def test_calculate_usefulness_score_trivial_content(self):
        """Test scoring of trivial content."""
        memory_block = Mock()
        memory_block.content = "Everything worked fine, no issues encountered"
        memory_block.retrieval_count = 0
        memory_block.created_at = datetime.now() - timedelta(days=365)
        memory_block.archived = False
        memory_block.consolidation_status = "none"
        
        # Mock LLM response for trivial content
        mock_llm_response = {
            "criticality": 2,
            "information_value": 1,
            "redundancy": 8,
            "temporal_relevance": 3
        }
        
        with patch('core.pruning.pruning_service.call_llm_with_prompt', return_value=mock_llm_response):
            score = calculate_usefulness_score(memory_block)
            assert isinstance(score, (int, float))
            assert 0 <= score <= 10
            # Should be low score for trivial content
            assert score < 5

    def test_pruning_service_initialization(self):
        """Test PruningService initialization."""
        mock_db = Mock()
        service = PruningService(mock_db)
        assert service.db == mock_db

    @patch('core.pruning.pruning_service.calculate_usefulness_score')
    @patch('core.pruning.pruning_service.call_llm_with_prompt')
    def test_generate_pruning_suggestions(self, mock_call_llm, mock_calculate_score):
        """Test generation of pruning suggestions."""
        # Mock database and LLM responses
        mock_db = Mock()
        mock_call_llm.return_value = {
            "criticality": 5,
            "information_value": 3,
            "redundancy": 7,
            "temporal_relevance": 4
        }
        mock_calculate_score.return_value = 3.5
        
        # Mock memory blocks
        mock_memory_blocks = []
        for i in range(5):
            block = Mock()
            block.id = str(uuid.uuid4())
            block.content = f"Test memory block {i}"
            block.created_at = datetime.now() - timedelta(days=i*30)
            block.archived = False
            block.retrieval_count = i
            mock_memory_blocks.append(block)
        
        mock_db.query().filter().order_by().limit().all.return_value = mock_memory_blocks
        
        service = PruningService(mock_db)
        
        # Test with small batch size
        suggestions = service.generate_pruning_suggestions(batch_size=3, target_count=2)
        
        assert isinstance(suggestions, list)
        # Should return up to batch_size suggestions
        assert len(suggestions) <= 3
        if suggestions:
            assert 'id' in suggestions[0]
            assert 'score' in suggestions[0]
            assert 'content' in suggestions[0]

if __name__ == '__main__':
    pytest.main([__file__])
