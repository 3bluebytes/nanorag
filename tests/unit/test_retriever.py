from datetime import UTC, datetime

from rag_nano.components.embedding import MockEmbeddingProvider
from rag_nano.components.retriever import CosineTopKRetriever
from rag_nano.components.structured_store import InMemoryStructuredStore
from rag_nano.components.vector_store import InMemoryVectorStore
from rag_nano.types import (
    DataType,
    KnowledgeChunk,
    KnowledgeSource,
    RetrievalFilters,
    RetrievalQuery,
)


class TestCosineTopKRetriever:
    def _make_indexed_store(self):
        structured = InMemoryStructuredStore()
        vector = InMemoryVectorStore()
        embed = MockEmbeddingProvider(dim=4)

        source = KnowledgeSource(
            source_id="s1",
            source_path="faq/embedding.md",
            data_type=DataType.faq,
            category="embedding",
            content_hash="abc",
            ingested_at=datetime.now(UTC),
            chunk_count=2,
        )
        chunks = [
            KnowledgeChunk(
                chunk_id="c1",
                source_id="s1",
                text="BGE-m3 query prefix",
                position=0,
                embedding_index=0,
                data_type=DataType.faq,
                category="embedding",
            ),
            KnowledgeChunk(
                chunk_id="c2",
                source_id="s1",
                text="FAQ about reranking",
                position=1,
                embedding_index=1,
                data_type=DataType.faq,
                category="embedding",
            ),
        ]
        structured.insert_source(source)
        structured.insert_chunks(chunks)

        texts = [c.text for c in chunks]
        embs = embed.encode(texts)
        vector.add([c.chunk_id for c in chunks], embs)

        return structured, vector, embed

    def test_basic_retrieval(self) -> None:
        structured, vector, embed = self._make_indexed_store()
        retriever = CosineTopKRetriever()
        query = RetrievalQuery(query="BGE-m3 query prefix", k=2)
        results = retriever.retrieve(query, embed, vector, structured)

        assert len(results) > 0
        assert all(r.chunk_id for r in results)
        assert all(r.source_path for r in results)

    def test_filter_by_data_type(self) -> None:
        structured, vector, embed = self._make_indexed_store()
        retriever = CosineTopKRetriever()
        query = RetrievalQuery(
            query="BGE-m3", k=5, filters=RetrievalFilters(data_types=[DataType.sop])
        )
        results = retriever.retrieve(query, embed, vector, structured)
        assert results == []

    def test_k_bounds(self) -> None:
        structured, vector, embed = self._make_indexed_store()
        retriever = CosineTopKRetriever()
        query = RetrievalQuery(query="BGE-m3 query prefix", k=1)
        results = retriever.retrieve(query, embed, vector, structured)
        assert len(results) <= 1
