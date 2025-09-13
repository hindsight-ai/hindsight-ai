"""
Lightweight keyword extraction utilities used by repositories.

Provides a simple, dependency-free heuristic extractor to avoid spaCy/runtime
weight while still enabling deterministic keyword suggestions.
"""
from typing import List, Optional
import re


def simple_extract_keywords(text: Optional[str]) -> List[str]:
    """Extract up to 10 lowercase tokens (>=3 chars) from the text.

    - Alphanumeric with optional dashes/underscores
    - Lowercases input
    - De-duplicates while preserving first occurrence ordering
    """
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
    seen = set()
    out: List[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= 10:
            break
    return out

