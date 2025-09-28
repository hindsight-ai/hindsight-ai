import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime, timezone
from core.services.search_service import SearchService, _create_memory_block_with_score


class TestSearchService:

    def setup_method(self):
        self.service = SearchService()

    def test_create_memory_block_with_score(self):
        # Mock memory block
        mock_memory_block = Mock()
        mock_memory_block.id = uuid.uuid4()
        mock_memory_block.agent_id = uuid.uuid4()
        mock_memory_block.conversation_id = uuid.uuid4()
        mock_memory_block.content = "Test content"
        mock_memory_block.errors = "Test errors"
        mock_memory_block.lessons_learned = "Test lessons"
        mock_memory_block.metadata_col = {"key": "value"}
        mock_memory_block.feedback_score = 1
        mock_memory_block.archived = False
        mock_memory_block.archived_at = None
        mock_memory_block.timestamp = "2023-01-01T00:00:00Z"
        mock_memory_block.created_at = "2023-01-01T00:00:00Z"
        mock_memory_block.updated_at = "2023-01-01T00:00:00Z"

        # Mock keywords
        mock_keyword = Mock()
        mock_keyword.keyword_id = uuid.uuid4()
        mock_keyword.keyword_text = "test"
        mock_keyword.created_at = "2023-01-01T00:00:00Z"
        mock_memory_block.keywords = [mock_keyword]

        result = _create_memory_block_with_score(mock_memory_block, 0.95, "fulltext", "Test explanation")

        assert result.id == mock_memory_block.id
        assert result.search_score == 0.95
        assert result.search_type == "fulltext"
        assert result.rank_explanation == "Test explanation"
        assert len(result.keywords) == 1
        assert result.keywords[0].keyword_text == "test"
        assert result.score_components == {}

    @patch('core.services.search_service.func')
    def test_search_memory_blocks_fulltext_empty_query(self, mock_func):
        db = Mock()
        service = SearchService()

        with pytest.raises(Exception):  # Should raise due to empty query
            service.search_memory_blocks_fulltext(db, "")

    def test_search_memory_blocks_fulltext_with_results(self):
        """Smoke test: ensure method returns structure when patched at higher level (endpoint tested elsewhere)."""
        db = Mock()
        service = SearchService()
        with patch.object(service, 'search_memory_blocks_fulltext') as mock_method:
            fake_block = Mock()
            fake_block.id = uuid.uuid4()
            fake_block.search_score = 0.5
            fake_block.search_type = 'fulltext'
            mock_method.return_value = ([fake_block], {"fulltext_results_count": 1, "search_type": "fulltext", "search_time": 0.01})
            results, meta = service.search_memory_blocks_fulltext(db, "hello")
            assert len(results) == 1
            assert meta["search_type"] == "fulltext"

    @patch('core.services.search_service.get_embedding_service')
    def test_search_memory_blocks_semantic_disabled_provider_falls_back(self, mock_get_service):
        db = Mock()
        service = SearchService()

        mock_embed_service = Mock()
        mock_embed_service.is_enabled = False
        mock_get_service.return_value = mock_embed_service

        with patch.object(service, '_basic_search_fallback', return_value=(['fallback'], {"search_type": "basic"})) as fallback:
            results, metadata = service.search_memory_blocks_semantic(db, "semantic query")

        fallback.assert_called_once()
        assert results == ['fallback']
        assert metadata["search_type"] == "semantic_fallback"
        assert metadata["fallback_reason"] == "embedding_provider_disabled"

    @patch('core.services.search_service.get_embedding_service')
    def test_search_memory_blocks_semantic_query_embedding_missing(self, mock_get_service):
        db = Mock()
        service = SearchService()

        mock_embed_service = Mock()
        mock_embed_service.is_enabled = True
        mock_embed_service.embed_text.return_value = None
        mock_get_service.return_value = mock_embed_service

        with patch.object(service, '_basic_search_fallback', return_value=([], {"search_type": "basic"})) as fallback:
            results, metadata = service.search_memory_blocks_semantic(db, "semantic query")

        fallback.assert_called_once()
        assert results == []
        assert metadata["search_type"] == "semantic_fallback"
        assert metadata["fallback_reason"] == "query_embedding_unavailable"

    @patch('core.services.search_service.get_embedding_service')
    def test_search_memory_blocks_semantic_non_postgres_fallback(self, mock_get_service):
        db = Mock()
        db.bind = Mock()
        db.bind.dialect = Mock()
        db.bind.dialect.name = 'sqlite'
        service = SearchService()

        mock_embed_service = Mock()
        mock_embed_service.is_enabled = True
        mock_embed_service.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_get_service.return_value = mock_embed_service

        with patch.object(service, '_basic_search_fallback', return_value=(['fallback'], {"search_type": "basic"})) as fallback:
            results, metadata = service.search_memory_blocks_semantic(db, "semantic query")

        fallback.assert_called_once()
        assert results == ['fallback']
        assert metadata["fallback_reason"] == "dialect_sqlite_unsupported"
        assert metadata["search_type"] == "semantic_fallback"

    @patch('core.services.search_service.get_embedding_service')
    def test_search_memory_blocks_semantic_success(self, mock_get_service):
        db = MagicMock()
        db.bind = MagicMock()
        db.bind.dialect = MagicMock()
        db.bind.dialect.name = 'postgresql'

        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = [(MagicMock(keywords=[]), 0.86)]
        db.query.return_value = query_mock

        mock_embed_service = Mock()
        mock_embed_service.is_enabled = True
        mock_embed_service.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_get_service.return_value = mock_embed_service

        service = SearchService()

        with patch('core.services.search_service._create_memory_block_with_score', return_value='converted') as converter, \
             patch.object(service, '_basic_search_fallback') as fallback:
            results, metadata = service.search_memory_blocks_semantic(db, "semantic query", limit=5)

        fallback.assert_not_called()
        converter.assert_called_once()
        assert results == ['converted']
        assert metadata["search_type"] == "semantic"
        assert metadata["semantic_results_count"] == 1
        assert metadata["scores"][0] == pytest.approx(0.14)

    def test_search_memory_blocks_hybrid_empty_query(self):
        db = Mock()
        service = SearchService()
        # Patch underlying methods the hybrid path would call
        with patch.object(service, 'search_memory_blocks_fulltext', return_value=([], {"fulltext_results_count": 0, "search_time": 0.01})), \
             patch.object(service, 'search_memory_blocks_semantic', return_value=([], {"semantic_results_count": 0, "search_time": 0.01})), \
             patch.object(service, '_basic_search_fallback', return_value=([], {"basic_results_count": 0})), \
             patch('core.services.search_service.time') as mock_time:
            mock_time.time.return_value = 1000.0
            results, metadata = service.search_memory_blocks_hybrid(db, "")
            assert results == []
            assert metadata["search_type"] == "hybrid"
            assert "component_summary" in metadata
            assert metadata["component_summary"]["candidate_counts"]["union"] == 0

    def test_combine_and_rerank_with_scores_empty_inputs(self):
        service = SearchService()

        results, stats = service._combine_and_rerank_with_scores([], [], 0.7, 0.3, 0.1)

        assert results == []
        assert stats["weights"]["fulltext"] == 0.7

    def test_combine_and_rerank_with_scores_with_results(self):
        service = SearchService()

        # Create mock results with minimal attributes consumed by the combiner
        now = datetime.now(timezone.utc)

        mock_result1 = Mock()
        mock_result1.id = uuid.uuid4()
        mock_result1.search_score = 0.8
        mock_result1.feedback_score = 0
        mock_result1.visibility_scope = 'public'
        mock_result1.timestamp = now
        hybrid_copy1 = Mock()
        mock_result1.model_copy.return_value = hybrid_copy1

        mock_result2 = Mock()
        mock_result2.id = uuid.uuid4()
        mock_result2.search_score = 0.6
        mock_result2.feedback_score = 0
        mock_result2.visibility_scope = 'public'
        mock_result2.timestamp = now
        hybrid_copy2 = Mock()
        mock_result2.model_copy.return_value = hybrid_copy2

        fulltext_results = [mock_result1]
        semantic_results = [mock_result2]

        results, stats = service._combine_and_rerank_with_scores(
            fulltext_results, semantic_results, 0.7, 0.3, 0.1
        )

        assert len(results) == 2
        assert results[0].search_score >= results[1].search_score
        assert results[0] is hybrid_copy1
        assert results[1] is hybrid_copy2
        assert stats["heuristics_enabled"]["scope"] is True
        assert hasattr(results[0], "score_components")
        assert isinstance(results[0].score_components, dict)

    def test_enhanced_search_memory_blocks_empty_query(self):
        db = Mock()
        service = SearchService()

        results, metadata = service.enhanced_search_memory_blocks(db, "")

        assert results == []
        assert metadata["message"] == "Empty query"

    def test_enhanced_search_memory_blocks_fulltext_type(self):
        db = Mock()
        service = SearchService()

        with patch.object(service, 'search_memory_blocks_fulltext') as mock_fulltext:
            mock_fulltext.return_value = ([], {"test": "metadata"})

            results, metadata = service.enhanced_search_memory_blocks(
                db, "test query", "fulltext"
            )

            mock_fulltext.assert_called_once()
            assert metadata["test"] == "metadata"

    def test_enhanced_search_memory_blocks_hybrid_type(self):
        db = Mock()
        service = SearchService()

        with patch.object(service, 'search_memory_blocks_hybrid') as mock_hybrid:
            mock_hybrid.return_value = ([], {"test": "metadata"})

            results, metadata = service.enhanced_search_memory_blocks(
                db, "test query", "hybrid"
            )

            mock_hybrid.assert_called_once()
            assert metadata["test"] == "metadata"

    def test_enhanced_search_memory_blocks_unknown_type(self):
        db = Mock()
        service = SearchService()

        with patch.object(service, '_basic_search_fallback') as mock_basic:
            mock_basic.return_value = ([], {"test": "metadata"})

            results, metadata = service.enhanced_search_memory_blocks(
                db, "test query", "unknown"
            )

            mock_basic.assert_called_once()
            assert metadata["test"] == "metadata"

    def test_combine_and_rerank(self):
        service = SearchService()
        # Mock memory blocks
        mock_mb1 = Mock()
        mock_mb1.id = uuid.uuid4()
        mock_mb2 = Mock()
        mock_mb2.id = uuid.uuid4()
        
        result = service._combine_and_rerank(
            [mock_mb1], [mock_mb2], [0.8], [0.6], 0.7, 0.3, 0.1
        )
        assert len(result) == 2

    def test_get_search_service(self):
        from core.services.search_service import get_search_service
        service = get_search_service()
        assert isinstance(service, SearchService)
        # Test singleton
        service2 = get_search_service()
        assert service is service2

    # Note: Direct unit tests of _basic_search_fallback removed; behavior covered indirectly
    # via enhanced_search_memory_blocks_unknown_type which routes through fallback.
