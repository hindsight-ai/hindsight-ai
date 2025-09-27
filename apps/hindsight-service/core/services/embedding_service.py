"""Embedding provider abstraction used for semantic retrieval."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

import requests

from core.db import models

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = (3, 60)


@dataclass
class EmbeddingConfig:
    provider: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    dimension: Optional[int] = None

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        provider = (os.getenv("EMBEDDING_PROVIDER") or "disabled").strip().lower()
        dimension = os.getenv("EMBEDDING_DIMENSION")
        dim_value = int(dimension) if dimension and dimension.isdigit() else None

        if provider == "ollama":
            return cls(
                provider=provider,
                model=os.getenv("OLLAMA_EMBEDDING_MODEL", "dengcao/Qwen3-Embedding-0.6B:Q8_0"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                dimension=dim_value,
            )
        if provider in {"huggingface", "hf"}:
            return cls(
                provider="huggingface",
                model=os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
                base_url=os.getenv("HUGGINGFACE_API_BASE", "https://api-inference.huggingface.co"),
                api_key=os.getenv("HUGGINGFACE_API_KEY"),
                dimension=dim_value,
            )
        if provider == "mock":
            return cls(provider=provider, dimension=dim_value or 32)
        if provider in {"disabled", "none", "off", ""}:
            return cls(provider="disabled")
        logger.warning("Unknown EMBEDDING_PROVIDER '%s'; embeddings disabled.", provider)
        return cls(provider="disabled")

    @property
    def is_enabled(self) -> bool:
        if self.provider == "disabled":
            return False
        if self.provider == "huggingface" and not self.api_key:
            logger.warning("HUGGINGFACE_API_KEY must be set for HuggingFace embeddings; disabling provider.")
            return False
        return True


class BaseEmbeddingProvider:
    dimension: Optional[int] = None

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_many(self, texts: Sequence[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class MockEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, dimension: int = 32) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: List[float] = []
        for i in range(self.dimension):
            byte = digest[i % len(digest)]
            values.append((byte / 127.5) - 1.0)
        return values


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str, base_url: str, dimension: Optional[int] = None) -> None:
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.dimension = dimension

    def embed(self, text: str) -> List[float]:
        payload = {"model": self.model, "prompt": text}
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        vector = data.get("embedding")
        if not isinstance(vector, list):
            raise RuntimeError("Unexpected Ollama embedding response structure")
        return vector


class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str, base_url: str, api_key: str, dimension: Optional[int] = None) -> None:
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.dimension = dimension

    def embed(self, text: str) -> List[float]:
        url = f"{self.base_url}/models/{self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json={"inputs": text}, timeout=_DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        vector: Optional[List[float]] = None
        if isinstance(payload, list):
            if payload and isinstance(payload[0], list):
                vector = payload[0]
            elif all(isinstance(x, (int, float)) for x in payload):
                vector = payload
        elif isinstance(payload, dict):
            embeddings = payload.get("embeddings")
            if isinstance(embeddings, list):
                vector = embeddings
            else:
                data = payload.get("data")
                if isinstance(data, list) and data:
                    item = data[0]
                    if isinstance(item, dict) and isinstance(item.get("embedding"), list):
                        vector = item["embedding"]
        if vector is None:
            raise RuntimeError("Unable to parse HuggingFace embedding response")
        return vector


class EmbeddingService:
    """High-level embedding helper used by repository code."""

    def __init__(self, config: Optional[EmbeddingConfig] = None) -> None:
        self.config = config or EmbeddingConfig.from_env()
        self._provider = self._build_provider()
        self._lock = threading.Lock()

    def _build_provider(self) -> Optional[BaseEmbeddingProvider]:
        if not self.config.is_enabled:
            return None
        provider = self.config.provider
        if provider == "ollama":
            return OllamaEmbeddingProvider(
                model=self.config.model or "nomic-embed-text",
                base_url=self.config.base_url or "http://localhost:11434",
                dimension=self.config.dimension,
            )
        if provider == "huggingface":
            assert self.config.api_key, "HuggingFace API key required"
            return HuggingFaceEmbeddingProvider(
                model=self.config.model or "sentence-transformers/all-MiniLM-L6-v2",
                base_url=self.config.base_url or "https://api-inference.huggingface.co",
                api_key=self.config.api_key,
                dimension=self.config.dimension,
            )
        if provider == "mock":
            return MockEmbeddingProvider(dimension=self.config.dimension or 32)
        return None

    @property
    def is_enabled(self) -> bool:
        return self._provider is not None

    def embedding_dimension(self) -> Optional[int]:
        if self._provider is None:
            return None
        return getattr(self._provider, "dimension", self.config.dimension)

    def embed_text(self, text: str) -> Optional[List[float]]:
        if not self._provider:
            return None
        if not text.strip():
            return None
        with self._lock:
            vector = self._provider.embed(text)
        return vector

    def compose_memory_text(self, memory_block: models.MemoryBlock) -> str:
        parts: List[str] = []
        if memory_block.content:
            parts.append(memory_block.content)
        if memory_block.lessons_learned:
            parts.append(memory_block.lessons_learned)
        if memory_block.errors:
            parts.append(f"Errors: {memory_block.errors}")
        if memory_block.metadata_col:
            try:
                parts.append(json.dumps(memory_block.metadata_col, sort_keys=True))
            except Exception:  # pragma: no cover - defensive
                pass
        return "\n\n".join(p for p in parts if p)

    def embed_memory_block(self, memory_block: models.MemoryBlock) -> Optional[List[float]]:
        text = self.compose_memory_text(memory_block)
        return self.embed_text(text)

    def attach_embedding(self, memory_block: models.MemoryBlock, *, save_empty: bool = False) -> None:
        if not self.is_enabled:
            return
        try:
            vector = self.embed_memory_block(memory_block)
        except Exception as exc:  # pragma: no cover - network failure path
            logger.error("Failed to compute embedding for memory %s: %s", getattr(memory_block, 'id', 'unknown'), exc)
            return
        if vector is None:
            if save_empty:
                memory_block.content_embedding = None
            return
        memory_block.content_embedding = vector

    def backfill_missing_embeddings(self, db_session, *, batch_size: int = 100) -> int:
        if not self.is_enabled:
            logger.info("Embedding service disabled; skipping backfill.")
            return 0
        run_started = time.perf_counter()
        updated = 0
        batch_count = 0
        while True:
            batch = (
                db_session.query(models.MemoryBlock)
                .filter(models.MemoryBlock.content_embedding.is_(None))
                .order_by(models.MemoryBlock.created_at.asc())
                .limit(batch_size)
                .all()
            )
            if not batch:
                break
            batch_count += 1
            batch_started = time.perf_counter()
            batch_updated = 0
            batch_errors: List[str] = []
            for memory_block in batch:
                try:
                    self.attach_embedding(memory_block, save_empty=True)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Embedding backfill error for %s: %s", memory_block.id, exc)
                    batch_errors.append(str(memory_block.id))
                    continue
                updated += 1
                batch_updated += 1
            db_session.commit()
            duration = time.perf_counter() - batch_started
            logger.info(
                "Embedding backfill batch committed",
                extra={
                    "batch_number": batch_count,
                    "batch_size": len(batch),
                    "updated_rows": batch_updated,
                    "duration_seconds": round(duration, 3),
                    "failed_ids": batch_errors,
                },
            )
        total_duration = time.perf_counter() - run_started
        logger.info(
            "Embedding backfill completed",
            extra={
                "batches": batch_count,
                "total_updated": updated,
                "duration_seconds": round(total_duration, 3),
            },
        )
        return updated


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service_for_tests() -> None:  # pragma: no cover - used in tests
    global _embedding_service
    _embedding_service = None
