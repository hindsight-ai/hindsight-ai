from core.utils.keywords import simple_extract_keywords


def test_simple_extract_keywords_empty_and_small_tokens():
    assert simple_extract_keywords(None) == []
    assert simple_extract_keywords("") == []
    # Too-short tokens should be ignored
    assert simple_extract_keywords("a b c ab ac _-!") == []


def test_simple_extract_keywords_dedup_and_limit():
    text = "Python python3 PYTHON python-ml python_ml test test-driven development development data data data"
    kws = simple_extract_keywords(text)
    # Dedup preserves order of first occurrences
    assert kws[0] == "python"
    assert len(kws) <= 10
    assert "development" in kws

