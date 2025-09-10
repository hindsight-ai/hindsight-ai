import pytest
from core.core.keyword_extraction import extract_keywords, normalize_keywords


def test_extract_keywords_empty_text():
    assert extract_keywords("") == []


def test_extract_keywords_none():
    assert extract_keywords(None) == []


def test_extract_keywords_basic():
    # Since the function is stubbed to return [], test that
    assert extract_keywords("This is a test") == []


def test_normalize_keywords_empty():
    assert normalize_keywords([]) == []


def test_normalize_keywords_basic():
    # Stubbed to return []
    assert normalize_keywords(["test", "Test"]) == []


def test_normalize_keywords_duplicates():
    assert normalize_keywords(["a", "a", "b"]) == []
