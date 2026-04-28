from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np

from rag_nano.config import Settings

logger = logging.getLogger(__name__)


class LocalSentenceTransformerProvider:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model", extra={"model": self.model_name})
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str], task: str = "passage") -> Any:
        model = self._load()
        prefixed = [_prefix(t, task) for t in texts]
        embeddings = model.encode(prefixed, normalize_embeddings=True)
        return np.asarray(embeddings, dtype=np.float32)


class MockEmbeddingProvider:
    def __init__(self, dim: int = 768) -> None:
        self.dim = dim

    def encode(self, texts: list[str], task: str = "passage") -> Any:
        rng = np.random.default_rng(_seed_from_texts(texts))
        embeddings = rng.standard_normal((len(texts), self.dim)).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return embeddings / norms


def _prefix(text: str, task: str) -> str:
    if task == "query":
        return f"query: {text}"
    return f"passage: {text}"


def _seed_from_texts(texts: list[str]) -> int:
    h = hashlib.sha256("".join(texts).encode()).hexdigest()
    return int(h[:16], 16)


def get_embedding_provider(settings: Settings) -> Any:
    if settings.embedding_backend == "local":
        return LocalSentenceTransformerProvider(settings.embedding_model)
    if settings.embedding_backend == "mock":
        return MockEmbeddingProvider()
    raise ValueError(f"Unknown embedding backend: {settings.embedding_backend}")
