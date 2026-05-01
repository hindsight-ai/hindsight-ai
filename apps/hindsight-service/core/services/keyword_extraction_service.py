"""
Keyword extraction service.

Single canonical implementation for keyword extraction across the
backend. Used by bulk keyword generation, the per-block suggest endpoint,
and the memory-optimization keyword suggestion path.

Public API: `extract_keywords(text, max_keywords=10)`. The legacy alias
`extract_keywords_enhanced` is preserved for backwards compatibility with
existing callers and patch points.
"""
import re
from collections import Counter
from typing import List


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Enhanced keyword extraction using simple text analysis.
    This is a fallback function when spaCy is not available.
    """
    if not text or not text.strip():
        return []

    # Clean and normalize text
    text = text.lower()

    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
        'his', 'hers', 'its', 'our', 'their', 'myself', 'yourself', 'himself', 'herself', 'itself',
        'ourselves', 'yourselves', 'themselves', 'what', 'which', 'who', 'whom', 'whose', 'where',
        'when', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'now', 'here', 'there', 'then', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
        'further', 'once', 'during', 'before', 'after', 'above', 'below', 'between', 'through',
        'into', 'from', 'about', 'against', 'within', 'without'
    }

    # Extract words (alphanumeric sequences of 3+ characters)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)

    # Filter out stop words and get word frequencies
    meaningful_words = [word for word in words if word not in stop_words]
    word_freq = Counter(meaningful_words)

    # Look for technical terms, proper nouns (capitalized words in original text), and domain-specific keywords
    technical_patterns = [
        r'\b(?:api|database|server|client|service|system|process|function|method|class|object|data|model|algorithm|framework|library|module|component|interface|protocol|network|security|authentication|authorization|token|session|cache|memory|storage|disk|cpu|gpu|performance|optimization|configuration|deployment|environment|production|development|testing|debugging|logging|monitoring|analytics|metrics|dashboard|report|analysis|query|search|filter|sort|pagination|validation|error|exception|warning|info|debug|trace)\b',
        r'\b(?:python|javascript|typescript|java|c\+\+|golang|rust|php|ruby|html|css|sql|json|xml|yaml|api|rest|graphql|http|https|tcp|udp|websocket|oauth|jwt|ssl|tls|aws|azure|gcp|docker|kubernetes|git|github|gitlab|jenkins|terraform|ansible|nginx|apache|postgresql|mysql|mongodb|redis|elasticsearch|kafka|rabbitmq|react|vue|angular|node|express|flask|django|fastapi|spring|laravel)\b',
        r'\b(?:user|admin|client|customer|account|profile|settings|preferences|notification|email|password|login|logout|signup|registration|dashboard|home|page|view|screen|form|input|button|menu|navigation|header|footer|sidebar|modal|dialog|popup|tab|accordion|carousel|slider|chart|graph|table|list|grid|card|tile|widget|component)\b'
    ]

    # Find technical terms
    technical_words = set()
    for pattern in technical_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        technical_words.update(matches)

    # Combine high-frequency words with technical terms
    # Get top words by frequency (minimum frequency of 2 or if text is short, frequency of 1)
    min_freq = 2 if len(meaningful_words) > 20 else 1
    frequent_words = [word for word, count in word_freq.most_common(10) if count >= min_freq]

    # Combine and deduplicate
    keywords = list(set(frequent_words + list(technical_words)))

    # Sort by relevance (technical terms first, then by frequency)
    def keyword_score(word):
        tech_score = 10 if word.lower() in technical_words else 0
        freq_score = word_freq.get(word, 0)
        return tech_score + freq_score

    keywords.sort(key=keyword_score, reverse=True)

    # Return top keywords (default 8 to match original behaviour; honour max_keywords)
    return keywords[:max_keywords]


# Backward-compatible alias — pre-#82 callers used this name.
extract_keywords_enhanced = extract_keywords
