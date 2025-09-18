import uuid
import pytest

from core.workers.consolidation_worker import (
    analyze_duplicates_with_fallback,
    analyze_duplicates_with_llm,
    store_consolidation_suggestions,
)


def _mb(content: str, lessons: str = ""):  # simple memory block dict
    return {"id": uuid.uuid4(), "content": content, "lessons_learned": lessons, "keywords": []}


def test_analyze_duplicates_with_fallback_groups_similar_texts():
    blocks = [
        _mb("hello world", ""),
        _mb("hello world!", ""),
        _mb("completely different", ""),
    ]
    groups = analyze_duplicates_with_fallback(blocks)
    # At least the two similar items should be grouped
    assert any(len(g.get("memory_ids", [])) >= 2 for g in groups)


def test_analyze_duplicates_with_llm_without_key_returns_fallback_groups():
    blocks = [
        _mb("alpha beta gamma", ""),
        _mb("alpha beta gamma", "more"),
    ]
    # No API key / model: function should catch and return fallback groups
    groups = analyze_duplicates_with_llm(blocks, llm_api_key="")
    assert isinstance(groups, list)
    assert all("group_id" in g for g in groups)


@pytest.mark.usefixtures("db_session")
def test_store_consolidation_suggestions_skips_without_llm_content(db_session):
    # Two groups, both missing LLM fields -> skipped
    groups = [
        {"group_id": str(uuid.uuid4()), "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
        {"group_id": str(uuid.uuid4()), "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
    ]
    created = store_consolidation_suggestions(db_session, groups)
    assert created == 0


@pytest.mark.usefixtures("db_session")
def test_store_consolidation_suggestions_creates_when_llm_content_present(db_session):
    gid = str(uuid.uuid4())
    groups = [
        {
            "group_id": gid,
            "memory_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "suggested_content": "S",
            "suggested_lessons_learned": "L",
            "suggested_keywords": ["k1", "k2"],
        }
    ]
    created = store_consolidation_suggestions(db_session, groups)
    assert created == 1
    # Re-submitting overlapping group should not create duplicates
    created2 = store_consolidation_suggestions(db_session, groups)
    assert created2 == 0

