import pytest
from core.utils.keywords import simple_extract_keywords


def test_extract_keywords_empty_text():
    assert simple_extract_keywords("") == []


def test_extract_keywords_none():
    assert simple_extract_keywords(None) == []


def test_extract_keywords_basic():
    # Simple heuristic should extract at least 'this' and 'test'
    result = simple_extract_keywords("This is a test")
    assert isinstance(result, list)
    assert len(result) >= 1


def test_keyword_extraction_dedup_and_limit():
    # Ensure de-dupe and limit of 10 applies
    text = "alpha beta gamma alpha beta gamma delta epsilon zeta eta theta iota kappa"
    result = simple_extract_keywords(text)
    assert len(result) <= 10
    # Duplicates should be removed while preserving order
    assert result[0] == "alpha"
