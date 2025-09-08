import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
from core.core.consolidation_worker import (
    fetch_memory_blocks,
    analyze_duplicates_with_fallback,
    store_consolidation_suggestions,
    run_consolidation_analysis
)


class TestConsolidationWorker:

    @patch('core.core.consolidation_worker.get_all_memory_blocks')
    def test_fetch_memory_blocks_success(self, mock_get_all):
        # Mock memory blocks as objects with __dict__
        class MockBlock:
            def __init__(self, id_val, content):
                self.id = id_val
                self.content = content

        mock_blocks = [
            MockBlock(uuid.uuid4(), 'Test content 1'),
            MockBlock(uuid.uuid4(), 'Test content 2')
        ]
        mock_get_all.return_value = mock_blocks

        db = Mock()
        result = fetch_memory_blocks(db, 0, 100)

        assert len(result) == 2
        assert 'id' in result[0]
        assert 'content' in result[0]
        mock_get_all.assert_called_once_with(db, skip=0, limit=100)

    @patch('core.core.consolidation_worker.get_all_memory_blocks')
    def test_fetch_memory_blocks_empty(self, mock_get_all):
        mock_get_all.return_value = []

        db = Mock()
        result = fetch_memory_blocks(db, 0, 100)

        assert result == []

    def test_analyze_duplicates_with_fallback_no_blocks(self):
        result = analyze_duplicates_with_fallback([])
        assert result == []

    def test_analyze_duplicates_with_fallback_single_block(self):
        blocks = [{'id': uuid.uuid4(), 'content': 'Single content'}]
        result = analyze_duplicates_with_fallback(blocks)
        assert result == []

    def test_analyze_duplicates_with_fallback_with_duplicates(self):
        block1_id = uuid.uuid4()
        block2_id = uuid.uuid4()
        blocks = [
            {'id': block1_id, 'content': 'This is a test content about AI', 'lessons_learned': 'AI is powerful'},
            {'id': block2_id, 'content': 'This is a test content about artificial intelligence', 'lessons_learned': 'AI is very powerful'}
        ]

        result = analyze_duplicates_with_fallback(blocks)

        # Should find at least one group with both blocks
        assert len(result) >= 1
        group = result[0]
        assert 'group_id' in group
        assert 'memory_ids' in group
        assert len(group['memory_ids']) > 1
        assert str(block1_id) in group['memory_ids']
        assert str(block2_id) in group['memory_ids']

    def test_analyze_duplicates_with_fallback_no_duplicates(self):
        block1_id = uuid.uuid4()
        block2_id = uuid.uuid4()
        blocks = [
            {'id': block1_id, 'content': 'This is about cats', 'lessons_learned': 'Cats are cute'},
            {'id': block2_id, 'content': 'This is about quantum physics', 'lessons_learned': 'Physics is complex'}
        ]

        result = analyze_duplicates_with_fallback(blocks)

        # Should find no groups
        assert len(result) == 0

    @patch('core.core.consolidation_worker.create_consolidation_suggestion')
    @patch('core.db.models.ConsolidationSuggestion')
    def test_store_consolidation_suggestions_success(self, mock_suggestion_model, mock_create):
        db = Mock()
        groups = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [str(uuid.uuid4()), str(uuid.uuid4())],
                'suggested_content': 'Consolidated content',
                'suggested_lessons_learned': 'Consolidated lessons',
                'suggested_keywords': ['keyword1', 'keyword2']
            }
        ]

        # Mock the database query chain
        mock_query = Mock()
        mock_filtered = Mock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filtered
        mock_filtered.all.return_value = []  # No existing suggestions

        result = store_consolidation_suggestions(db, groups)

        assert result == 1
        mock_create.assert_called_once()
        db.commit.assert_called_once()

    @patch('core.core.consolidation_worker.create_consolidation_suggestion')
    @patch('core.db.models.ConsolidationSuggestion')
    def test_store_consolidation_suggestions_overlap(self, mock_suggestion_model, mock_create):
        db = Mock()
        memory_id = str(uuid.uuid4())
        groups = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [memory_id, str(uuid.uuid4())],
                'suggested_content': 'Consolidated content',
                'suggested_lessons_learned': 'Consolidated lessons',
                'suggested_keywords': ['keyword1', 'keyword2']
            }
        ]

        # Mock existing suggestion with overlapping memory ID
        mock_existing = Mock()
        mock_existing.original_memory_ids = [memory_id]
        
        # Mock the database query chain
        mock_query = Mock()
        mock_filtered = Mock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filtered
        mock_filtered.all.return_value = [mock_existing]

        result = store_consolidation_suggestions(db, groups)

        assert result == 0
        mock_create.assert_not_called()

    @patch('core.core.consolidation_worker.create_consolidation_suggestion')
    @patch('core.db.models.ConsolidationSuggestion')
    def test_store_consolidation_suggestions_missing_content(self, mock_suggestion_model, mock_create):
        db = Mock()
        groups = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [str(uuid.uuid4()), str(uuid.uuid4())],
                'suggested_content': '',  # Missing content
                'suggested_lessons_learned': 'Consolidated lessons',
                'suggested_keywords': ['keyword1', 'keyword2']
            }
        ]

        # Mock the database query chain
        mock_query = Mock()
        mock_filtered = Mock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filtered
        mock_filtered.all.return_value = []  # No existing suggestions

        result = store_consolidation_suggestions(db, groups)

        assert result == 0
        mock_create.assert_not_called()

    @patch('core.core.consolidation_worker.create_consolidation_suggestion')
    @patch('core.db.models.ConsolidationSuggestion')
    def test_store_consolidation_suggestions_overlap(self, mock_suggestion_model, mock_create):
        db = Mock()
        memory_id = str(uuid.uuid4())
        groups = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [memory_id, str(uuid.uuid4())],
                'suggested_content': 'Consolidated content',
                'suggested_lessons_learned': 'Consolidated lessons',
                'suggested_keywords': ['keyword1', 'keyword2']
            }
        ]

        # Mock existing suggestion with overlapping memory ID
        mock_existing = Mock()
        mock_existing.original_memory_ids = [memory_id]
        
        mock_query = Mock()
        mock_suggestion_model.query = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_existing]
        mock_query = Mock()
        mock_suggestion_model.query = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_existing]

        result = store_consolidation_suggestions(db, groups)

        assert result == 0
        mock_create.assert_not_called()

    @patch('core.core.consolidation_worker.create_consolidation_suggestion')
    @patch('core.db.models.ConsolidationSuggestion')
    def test_store_consolidation_suggestions_missing_content(self, mock_suggestion_model, mock_create):
        db = Mock()
        groups = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [str(uuid.uuid4()), str(uuid.uuid4())],
                'suggested_content': '',  # Missing content
                'suggested_lessons_learned': 'Consolidated lessons',
                'suggested_keywords': ['keyword1', 'keyword2']
            }
        ]

        # Mock no existing suggestions
        mock_query = Mock()
        mock_suggestion_model.query = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = store_consolidation_suggestions(db, groups)

        assert result == 0
        mock_create.assert_not_called()

    @patch('core.core.consolidation_worker.create_consolidation_suggestion')
    @patch('core.db.models.ConsolidationSuggestion')
    def test_store_consolidation_suggestions_overlap(self, mock_suggestion_model, mock_create):
        db = Mock()
        memory_id = str(uuid.uuid4())
        groups = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [memory_id, str(uuid.uuid4())],
                'suggested_content': 'Consolidated content',
                'suggested_lessons_learned': 'Consolidated lessons',
                'suggested_keywords': ['keyword1', 'keyword2']
            }
        ]

        # Mock existing suggestion with overlapping memory ID
        mock_existing = Mock()
        mock_existing.original_memory_ids = [memory_id]

        result = store_consolidation_suggestions(db, groups)

        assert result == 0
        mock_create.assert_not_called()

    @patch('core.core.consolidation_worker.create_consolidation_suggestion')
    @patch('core.db.models.ConsolidationSuggestion')
    def test_store_consolidation_suggestions_missing_content(self, mock_suggestion_model, mock_create):
        db = Mock()
        groups = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [str(uuid.uuid4()), str(uuid.uuid4())],
                'suggested_content': '',  # Missing content
                'suggested_lessons_learned': 'Consolidated lessons',
                'suggested_keywords': ['keyword1', 'keyword2']
            }
        ]

        # Mock no existing suggestions
        mock_query = Mock()
        mock_suggestion_model.query = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = store_consolidation_suggestions(db, groups)

        assert result == 0
        mock_create.assert_not_called()

    @patch('core.core.consolidation_worker.fetch_memory_blocks')
    @patch('core.core.consolidation_worker.analyze_duplicates_with_llm')
    @patch('core.core.consolidation_worker.store_consolidation_suggestions')
    @patch('core.core.consolidation_worker.get_db')
    def test_run_consolidation_analysis_full_cycle(self, mock_get_db, mock_store, mock_analyze, mock_fetch):
        # Mock database
        db = Mock()
        mock_get_db.return_value = iter([db])

        # Mock fetch returning blocks then empty
        mock_fetch.side_effect = [
            [{'id': uuid.uuid4(), 'content': 'Test'}],
            []
        ]

        # Mock analysis returning groups
        mock_analyze.return_value = [
            {
                'group_id': str(uuid.uuid4()),
                'memory_ids': [str(uuid.uuid4())],
                'suggested_content': 'Consolidated',
                'suggested_lessons_learned': 'Lessons',
                'suggested_keywords': ['kw']
            }
        ]

        # Mock store returning 1
        mock_store.return_value = 1

        run_consolidation_analysis('fake_key')

        # Verify calls - it should call fetch once for the batch, then again for empty
        assert mock_fetch.call_count >= 1
        mock_analyze.assert_called_once()
        mock_store.assert_called_once()
        db.close.assert_called_once()

    @patch('core.core.consolidation_worker.fetch_memory_blocks')
    @patch('core.core.consolidation_worker.analyze_duplicates_with_llm')
    @patch('core.core.consolidation_worker.store_consolidation_suggestions')
    @patch('core.core.consolidation_worker.get_db')
    def test_run_consolidation_analysis_no_blocks(self, mock_get_db, mock_store, mock_analyze, mock_fetch):
        # Mock database
        db = Mock()
        mock_get_db.return_value = iter([db])

        # Mock fetch returning empty immediately
        mock_fetch.return_value = []

        run_consolidation_analysis('fake_key')

        # Verify no analysis or storage
        mock_analyze.assert_not_called()
        mock_store.assert_not_called()
        db.close.assert_called_once()
