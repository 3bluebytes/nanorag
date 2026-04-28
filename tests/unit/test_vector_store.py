import shutil

import numpy as np
import pytest

from rag_nano.components.vector_store import NumpyFlatVectorStore


class TestNumpyFlatVectorStore:
    def test_roundtrip_persistence(self, tmp_path) -> None:
        store = NumpyFlatVectorStore()
        store.add(
            ["c1", "c2", "c3"],
            np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32),
        )
        store.persist(tmp_path / "vectors")

        store2 = NumpyFlatVectorStore()
        store2.load(tmp_path / "vectors")
        assert store2.count() == 3

        results = store2.search(np.array([1, 0, 0], dtype=np.float32), k=1)
        assert results[0][0] == "c1"

    def test_cosine_top_k_correctness(self) -> None:
        store = NumpyFlatVectorStore()
        embeddings = np.array(
            [[1, 0, 0], [0.9, 0.1, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32
        )
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        store.add(["c1", "c2", "c3", "c4"], embeddings)

        query = np.array([1, 0, 0], dtype=np.float32)
        query = query / np.linalg.norm(query)
        results = store.search(query, k=2)

        ids = [r[0] for r in results]
        scores = [r[1] for r in results]
        assert ids == ["c1", "c2"]
        assert scores[0] > scores[1]
        assert scores[0] <= 1.0001

    def test_empty_store_returns_empty(self) -> None:
        store = NumpyFlatVectorStore()
        results = store.search(np.array([1, 0], dtype=np.float32), k=3)
        assert results == []

    def test_chunk_id_filter(self) -> None:
        store = NumpyFlatVectorStore()
        embeddings = np.array(
            [[1, 0, 0], [0.9, 0.1, 0], [0, 1, 0]], dtype=np.float32
        )
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        store.add(["c1", "c2", "c3"], embeddings)

        query = np.array([1, 0, 0], dtype=np.float32)
        query = query / np.linalg.norm(query)
        results = store.search(query, k=2, chunk_id_filter={"c2", "c3"})

        ids = [r[0] for r in results]
        assert "c1" not in ids
        assert ids == ["c2", "c3"] or ids == ["c2"]

    def test_atomic_rename_swap(self, tmp_path) -> None:
        store = NumpyFlatVectorStore()
        store.add(
            ["c1", "c2"],
            np.array([[1, 0], [0, 1]], dtype=np.float32),
        )
        store.persist(tmp_path / "vectors_next")

        target = tmp_path / "vectors"
        if target.exists():
            shutil.rmtree(target)
        (tmp_path / "vectors_next").rename(target)

        store2 = NumpyFlatVectorStore()
        store2.load(target)
        assert store2.count() == 2
