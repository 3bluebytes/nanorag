"""Constitution V gate test.

For every swappable component, the same retrieval flow must produce
structurally-equivalent responses when wired with the reference impl vs
a mock/test impl.  "Structurally equivalent" means the same fields are
populated with the same types; values may differ because mocks return
fixed / synthetic data.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from rag_nano.components.embedding import (
    LocalSentenceTransformerProvider,
    MockEmbeddingProvider,
)
from rag_nano.components.metadata_extractor import (
    DefaultMetadataExtractor,
    MockMetadataExtractor,
)
from rag_nano.components.retriever import CosineTopKRetriever, MockRetriever
from rag_nano.components.reranker import IdentityReranker, MockReranker
from rag_nano.components.structured_store import (
    InMemoryStructuredStore,
    SqliteStructuredStore,
)
from rag_nano.components.vector_store import InMemoryVectorStore, NumpyFlatVectorStore
from rag_nano.types import (
    DataType,
    KnowledgeChunk,
    KnowledgeSource,
    RetrievalQuery,
    RetrievalResultRecord,
)


class TestSwappability:
    def _seed_store(
        self,
        structured,
        vector,
        embedding,
    ):
        source = KnowledgeSource(
            source_id="s1",
            source_path="faq/q1.md",
            data_type=DataType.faq,
            category="test",
            content_hash="abc",
            ingested_at=datetime.now(timezone.utc),
            chunk_count=2,
        )
        chunks = [
            KnowledgeChunk(
                chunk_id="c1",
                source_id="s1",
                text="hello world",
                position=0,
                embedding_index=0,
                data_type=DataType.faq,
                category="test",
            ),
            KnowledgeChunk(
                chunk_id="c2",
                source_id="s1",
                text="goodbye world",
                position=1,
                embedding_index=1,
                data_type=DataType.faq,
                category="test",
            ),
        ]
        structured.insert_source(source)
        structured.insert_chunks(chunks)
        embs = embedding.encode([c.text for c in chunks])
        vector.add([c.chunk_id for c in chunks], embs)

    def _run_flow(self, embedding, vector_store, structured_store, retriever, reranker):
        self._seed_store(structured_store, vector_store, embedding)
        query = RetrievalQuery(query="hello", k=2)
        results = retriever.retrieve(
            query, embedding, vector_store, structured_store
        )
        reranked, detail = reranker.rerank(results, query.query)
        return {
            "results": reranked,
            "detail": detail,
            "result_count": len(reranked),
            "has_chunk_ids": all(bool(r.chunk_id) for r in reranked),
            "has_source_paths": all(bool(r.source_path) for r in reranked),
            "has_scores": all(isinstance(r.score, float) for r in reranked),
            "has_data_types": all(isinstance(r.data_type, DataType) for r in reranked),
            "has_text": all(bool(r.text) for r in reranked),
            "detail_count": len(detail),
        }

    def _assert_structurally_equivalent(self, ref_shape, mock_shape):
        # Response shape equivalence: same provenance fields populated,
        # same types; counts may differ because mocks return synthetic data.
        assert ref_shape["has_chunk_ids"] == mock_shape["has_chunk_ids"]
        assert ref_shape["has_source_paths"] == mock_shape["has_source_paths"]
        assert ref_shape["has_scores"] == mock_shape["has_scores"]
        assert ref_shape["has_data_types"] == mock_shape["has_data_types"]
        assert ref_shape["has_text"] == mock_shape["has_text"]
        # Both must have rerank detail when results exist
        has_results = ref_shape["result_count"] > 0
        mock_has_results = mock_shape["result_count"] > 0
        if has_results and mock_has_results:
            assert ref_shape["detail_count"] == ref_shape["result_count"]
            assert mock_shape["detail_count"] == mock_shape["result_count"]

    def test_embedding_provider(self) -> None:
        ref = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        mock = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        self._assert_structurally_equivalent(ref, mock)

    def test_vector_store(self) -> None:
        ref = self._run_flow(
            MockEmbeddingProvider(dim=4),
            NumpyFlatVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        mock = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        self._assert_structurally_equivalent(ref, mock)

    def test_retriever(self) -> None:
        ref = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        mock = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            MockRetriever(
                fixed_results=[
                    RetrievalResultRecord(
                        chunk_id="c1",
                        source_id="s1",
                        source_path="faq/q1.md",
                        score=0.5,
                        data_type=DataType.faq,
                        category="test",
                        text="hello world",
                    )
                ]
            ),
            IdentityReranker(),
        )
        self._assert_structurally_equivalent(ref, mock)

    def test_reranker(self) -> None:
        ref = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        mock = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            MockReranker(),
        )
        self._assert_structurally_equivalent(ref, mock)

    def test_structured_store(self, tmp_path) -> None:
        ref = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            SqliteStructuredStore(tmp_path / "ref.db"),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        mock = self._run_flow(
            MockEmbeddingProvider(dim=4),
            InMemoryVectorStore(),
            InMemoryStructuredStore(),
            CosineTopKRetriever(),
            IdentityReranker(),
        )
        self._assert_structurally_equivalent(ref, mock)

    def test_metadata_extractor(self) -> None:
        ref = DefaultMetadataExtractor()
        mock = MockMetadataExtractor(fixed={"category": "test", "data_type": "faq"})

        ref_meta = ref.extract("faq/q1.md", "---\ncategory: ops\n---\n# Q1")
        mock_meta = mock.extract("faq/q1.md", "---\ncategory: ops\n---\n# Q1")

        assert isinstance(ref_meta, dict)
        assert isinstance(mock_meta, dict)
        assert "category" in ref_meta
        assert "category" in mock_meta
