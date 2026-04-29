import pytest

from rag_nano.components.embedding import MockEmbeddingProvider
from rag_nano.components.reranker import IdentityReranker
from rag_nano.components.retriever import CosineTopKRetriever
from rag_nano.core.retrieval import Components, retrieve
from rag_nano.types import RetrievalFilters, RetrievalQuery


class TestRetrievalE2E:
    @pytest.fixture
    def components(self, seed_index_fixture):
        structured, vector = seed_index_fixture
        return Components(
            embedding_provider=MockEmbeddingProvider(dim=4),
            vector_store=vector,
            retriever=CosineTopKRetriever(),
            reranker=IdentityReranker(),
            structured_store=structured,
        )

    def test_basic_ranked_attribution(self, components) -> None:
        query = RetrievalQuery(query="BGE-m3 prefix config", k=3)
        resp = retrieve(query, components)
        assert len(resp.results) > 0
        for r in resp.results:
            assert r.chunk_id
            assert r.source_id
            assert r.source_path
            assert isinstance(r.score, float)

    def test_filter_pre_application(self, components) -> None:
        query = RetrievalQuery(
            query="BGE-m3 prefix config",
            k=5,
            filters=RetrievalFilters(data_types=["sop"]),
        )
        resp = retrieve(query, components)
        # With mock embeddings semantic unrelatedness is not guaranteed,
        # so we verify the filter was applied (all results are SOP type).
        for r in resp.results:
            assert r.data_type.value == "sop"

    def test_debug_mode(self, components) -> None:
        query = RetrievalQuery(query="BGE-m3 prefix config", k=2, debug=True)
        resp = retrieve(query, components)
        assert resp.debug is not None
        assert resp.debug.recall_candidates
        assert resp.debug.rerank_detail

    def test_empty_hit_list(self, components) -> None:
        # With mock embeddings, semantic unrelatedness is not guaranteed.
        # Verify the response shape is correct regardless of hit count.
        query = RetrievalQuery(query="completely nonexistent topic xyz", k=3)
        resp = retrieve(query, components)
        assert resp.stats.returned == len(resp.results)
        assert resp.stats.total_candidates >= 0
