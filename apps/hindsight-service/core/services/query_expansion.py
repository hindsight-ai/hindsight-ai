"""Query expansion engine used by search workflows."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

import requests
logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
_DEFAULT_SYNONYMS: Dict[str, List[str]] = {
    "bug": ["defect", "issue", "problem"],
    "bugs": ["defects", "issues", "problems"],
    "defect": ["bug", "issue"],
    "error": ["failure", "fault"],
    "failure": ["error", "fault"],
    "optimize": ["improve", "tune", "refine"],
    "optimization": ["improvement", "tuning"],
    "retry": ["replay", "rerun"],
    "database": ["db", "datastore"],
    "db": ["database", "datastore"],
    "performance": ["latency", "speed", "throughput"],
    "latency": ["performance", "response"],
    "speed": ["performance", "throughput"],
    "throughput": ["performance", "speed"],
    "deploy": ["release", "ship"],
    "release": ["deploy", "ship"],
    "fix": ["resolve", "repair"],
}


@dataclass(frozen=True)
class QueryExpansionConfig:
    """Configuration for the query expansion pipeline."""

    enabled: bool = True
    stemming_enabled: bool = True
    synonyms_enabled: bool = True
    llm_provider: Optional[str] = None
    max_expansions: int = 5
    llm_max_expansions: int = 2
    synonyms_path: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: str = "http://ollama:11434"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 64
    llm_timeout_seconds: float = 5.0

    @classmethod
    def from_environment(cls) -> "QueryExpansionConfig":
        return cls(
            enabled=_env_bool("QUERY_EXPANSION_ENABLED", True),
            stemming_enabled=_env_bool("QUERY_EXPANSION_STEMMING_ENABLED", True),
            synonyms_enabled=_env_bool("QUERY_EXPANSION_SYNONYMS_ENABLED", True),
            llm_provider=os.getenv("QUERY_EXPANSION_LLM_PROVIDER"),
            max_expansions=_env_int("QUERY_EXPANSION_MAX_VARIANTS", 5),
            llm_max_expansions=_env_int("QUERY_EXPANSION_LLM_MAX_VARIANTS", 2),
            synonyms_path=os.getenv("QUERY_EXPANSION_SYNONYMS_PATH"),
            llm_model=os.getenv("QUERY_EXPANSION_LLM_MODEL"),
            llm_base_url=os.getenv("QUERY_EXPANSION_OLLAMA_BASE_URL", "http://ollama:11434"),
            llm_temperature=_env_float("QUERY_EXPANSION_LLM_TEMPERATURE", 0.0),
            llm_max_tokens=_env_int("QUERY_EXPANSION_LLM_MAX_TOKENS", 64),
            llm_timeout_seconds=_env_float("QUERY_EXPANSION_LLM_TIMEOUT_SECONDS", 5.0),
        )


@dataclass
class QueryExpansionResult:
    original_query: str
    expanded_queries: List[str] = field(default_factory=list)
    applied_steps: List[Dict[str, Any]] = field(default_factory=list)
    disabled_reason: Optional[str] = None

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "expanded_queries": self.expanded_queries,
            "applied_steps": self.applied_steps,
            "disabled_reason": self.disabled_reason,
            "expansion_applied": bool(self.expanded_queries),
        }


class QueryExpansionEngine:
    """Simple query expansion pipeline with rule-based and optional LLM steps."""

    def __init__(self, config: Optional[QueryExpansionConfig] = None):
        self.config = config or QueryExpansionConfig.from_environment()
        self.synonyms = self._load_synonyms(self.config.synonyms_path)

    def expand(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryExpansionResult:
        query = (query or "").strip()
        if not query:
            return QueryExpansionResult(original_query="")

        if not self.config.enabled:
            return QueryExpansionResult(
                original_query=query,
                expanded_queries=[],
                applied_steps=[],
                disabled_reason="expansion_disabled",
            )

        result = QueryExpansionResult(original_query=query)
        seen: Set[str] = {query}
        max_variants = max(self.config.max_expansions, 0)

        def add_variant(variant: str, step: str, detail: Dict[str, Any]) -> None:
            if not variant:
                return
            normalized = variant.strip()
            if not normalized:
                return
            if normalized in seen:
                return
            if max_variants and len(result.expanded_queries) >= max_variants:
                return
            result.expanded_queries.append(normalized)
            result.applied_steps.append({"step": step, **detail, "variant": normalized})
            seen.add(normalized)

        if self.config.stemming_enabled:
            for variant, detail in self._stem_variants(query):
                add_variant(variant, "stemming", detail)

        if self.config.synonyms_enabled and self.synonyms:
            for variant, detail in self._synonym_variants(query):
                add_variant(variant, "synonym", detail)

        if self.config.llm_provider:
            for variant, detail in self._llm_variants(query, context):
                add_variant(variant, "llm_rewrite", detail)

        return result

    # ------------------------------------------------------------------
    # Expansion strategies

    def _stem_variants(self, query: str) -> Iterable[tuple[str, Dict[str, Any]]]:
        tokens = self._tokenize(query)
        stems: List[str] = []
        for token in tokens:
            stem = self._simple_stem(token)
            stems.append(stem)
        candidate = " ".join(stems)
        if candidate != query and candidate.strip():
            yield candidate, {"source": "suffix_rules"}

    def _synonym_variants(self, query: str) -> Iterable[tuple[str, Dict[str, Any]]]:
        tokens = self._tokenize(query)
        lowered = [token.lower() for token in tokens]
        for idx, token in enumerate(lowered):
            synonyms = self.synonyms.get(token)
            if not synonyms:
                continue
            for synonym in synonyms:
                new_tokens = tokens.copy()
                new_tokens[idx] = synonym
                variant = " ".join(new_tokens)
                if variant != query:
                    yield variant, {"token": tokens[idx], "synonym": synonym}

    def _llm_variants(self, query: str, context: Optional[Dict[str, Any]]) -> Iterable[tuple[str, Dict[str, Any]]]:
        provider = self.config.llm_provider
        if provider is None:
            return []

        provider_key = provider.lower()
        max_variants = max(self.config.llm_max_expansions, 0)
        if provider_key == "mock":
            # Lightweight deterministic rewrite for tests/local usage
            variant = f"{query} explained"
            yield variant, {"provider": "mock", "reason": "deterministic mock rewrite"}
            if max_variants > 1:
                variant2 = f"How to {query}" if not query.lower().startswith("how") else f"{query}?"
                yield variant2, {"provider": "mock", "reason": "mock heuristic"}
            return

        if provider_key == "ollama":
            yield from self._ollama_variants(query, context)
            return

        logger.warning("Query expansion LLM provider '%s' not implemented; skipping", provider)
        return []

    # ------------------------------------------------------------------
    def _ollama_variants(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
    ) -> Iterable[tuple[str, Dict[str, Any]]]:
        model = self.config.llm_model
        if not model:
            logger.warning("Ollama query expansion selected but QUERY_EXPANSION_LLM_MODEL is unset; skipping")
            return []

        base_url = (self.config.llm_base_url or "http://ollama:11434").rstrip("/")
        prompt = self._build_ollama_prompt(query, context)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": max(self.config.llm_temperature, 0.0),
                "top_p": 0.9,
                "num_predict": max(self.config.llm_max_tokens, 1),
                "repeat_penalty": 1.1,
            },
        }

        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json=payload,
                timeout=max(self.config.llm_timeout_seconds, 1.0),
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Query expansion Ollama call failed: %s", exc)
            return []

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("Query expansion Ollama response was not JSON: %s", exc)
            return []

        text = (data.get("response") or "").strip()
        if not text:
            return []

        emitted = 0
        max_variants = max(self.config.llm_max_expansions, 0)
        for line in text.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            candidate = re.sub(r"^[\s\-\d\.#:]+", "", candidate).strip()
            if not candidate or candidate.lower() == query.lower():
                continue
            if len(candidate) > 200:
                candidate = candidate[:200].rstrip()
            emitted += 1
            yield candidate, {
                "provider": "ollama",
                "model": model,
            }
            if max_variants and emitted >= max_variants:
                break

    def _build_ollama_prompt(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        contextual_hint = ""
        if context:
            try:
                context_json = json.dumps(context, default=str)
            except Exception:
                context_json = str(context)
            contextual_hint = (
                "\n\nContext (JSON metadata about the current search request):\n"
                f"{context_json}"
            )

        max_variants = max(self.config.llm_max_expansions, 1)
        return (
            "You expand search queries for a retrieval system."
            " Given the original query, produce up to"
            f" {max_variants} alternative phrasings that stay on topic,"
            " each on its own line without numbering or commentary."
            " Focus on synonyms, concise rewordings, and related terminology."
            " Avoid conversational fillers."
            f"\n\nOriginal query: {query.strip()}"
            f"{contextual_hint}\n\nExpanded queries:"
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _load_synonyms(path: Optional[str]) -> Dict[str, List[str]]:
        if path:
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if not isinstance(data, dict):
                    raise ValueError("expected mapping of word -> synonyms")
                normalized: Dict[str, List[str]] = {}
                for word, values in data.items():
                    if not isinstance(values, list):
                        continue
                    normalized[word.lower()] = [str(v) for v in values if str(v).strip()]
                return normalized or _DEFAULT_SYNONYMS
            except Exception as exc:
                logger.warning("Failed to load custom synonyms from %s: %s", path, exc)
        return _DEFAULT_SYNONYMS

    @staticmethod
    def _tokenize(query: str) -> List[str]:
        if not query:
            return []
        return re.findall(r"[\w']+", query)

    @staticmethod
    def _simple_stem(token: str) -> str:
        candidate = token
        for suffix in ("ing", "ers", "ies", "ed", "es", "s"):
            if candidate.lower().endswith(suffix) and len(candidate) > len(suffix) + 2:
                candidate = candidate[: -len(suffix)]
                break
        return candidate


_query_expansion_engine: Optional[QueryExpansionEngine] = None


def get_query_expansion_engine() -> QueryExpansionEngine:
    global _query_expansion_engine
    if _query_expansion_engine is None:
        _query_expansion_engine = QueryExpansionEngine()
    return _query_expansion_engine


def reset_query_expansion_engine_for_tests() -> None:
    global _query_expansion_engine
    _query_expansion_engine = None
