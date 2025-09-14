from core.utils.keywords import simple_extract_keywords


def test_simple_extract_keywords_basic_and_limits():
    assert simple_extract_keywords(None) == []
    text = "Alpha beta gamma, alpha-beta, gamma123 __ignore x y z toolong2short a-b-c"
    kws = simple_extract_keywords(text)
    # Lowercased, unique order, only valid tokens (>=3, alnum with dashes/underscores)
    assert "alpha" in kws and "beta" in kws and "gamma" in kws and "alpha-beta" in kws and "gamma123" in kws
    # limit to 10
    many = " ".join([f"tok{i}" for i in range(20)])
    assert len(simple_extract_keywords(many)) == 10

