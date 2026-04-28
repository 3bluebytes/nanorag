from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from rag_nano.config import Settings

logger = logging.getLogger(__name__)


class NumpyFlatVectorStore:
    def __init__(self) -> None:
        self._matrix: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self._id_map: list[str] = []

    def add(self, chunk_ids: list[str], embeddings: Any) -> None:
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be 2-D")
        if len(chunk_ids) != embeddings.shape[0]:
            raise ValueError("chunk_ids and embeddings length mismatch")
        if self._matrix.size == 0:
            self._matrix = embeddings
        else:
            if embeddings.shape[1] != self._matrix.shape[1]:
                raise ValueError("embedding dimension mismatch")
            self._matrix = np.vstack([self._matrix, embeddings])
        self._id_map.extend(chunk_ids)

    def search(
        self, query_embedding: Any, k: int, chunk_id_filter: set[str] | None = None
    ) -> list[tuple[str, float]]:
        if self._matrix.size == 0:
            return []
        query = np.asarray(query_embedding, dtype=np.float32)
        if query.ndim == 1:
            query = query.reshape(1, -1)
        scores = (self._matrix @ query.T).flatten()

        if chunk_id_filter is not None:
            mask = np.array([cid in chunk_id_filter for cid in self._id_map], dtype=bool)
            scores = np.where(mask, scores, -np.inf)

        k = min(k, len(self._id_map))
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        return [(self._id_map[i], float(scores[i])) for i in top_idx if scores[i] > -np.inf]

    def clear(self) -> None:
        self._matrix = np.zeros((0, 0), dtype=np.float32)
        self._id_map = []

    def persist(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        np.save(path / "matrix.npy", self._matrix)
        (path / "id_map.json").write_text(json.dumps(self._id_map), encoding="utf-8")
        manifest = {
            "dim": int(self._matrix.shape[1]) if self._matrix.ndim == 2 else 0,
            "chunk_count": len(self._id_map),
        }
        (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def load(self, path: Path) -> None:
        matrix_path = path / "matrix.npy"
        id_map_path = path / "id_map.json"
        if matrix_path.exists() and id_map_path.exists():
            self._matrix = np.load(matrix_path).astype(np.float32)
            self._id_map = json.loads(id_map_path.read_text(encoding="utf-8"))
        else:
            self.clear()

    def count(self) -> int:
        return len(self._id_map)


class InMemoryVectorStore(NumpyFlatVectorStore):
    def persist(self, path: Path) -> None:
        pass

    def load(self, path: Path) -> None:
        pass


def get_vector_store(settings: Settings) -> Any:
    if settings.vector_store == "numpy_flat":
        return NumpyFlatVectorStore()
    if settings.vector_store == "in_memory":
        return InMemoryVectorStore()
    raise ValueError(f"Unknown vector store: {settings.vector_store}")
