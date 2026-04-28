"""Constitution VII gate test.

Every returned hit must carry all 7 mandatory provenance fields.
"""

import random

import pytest

from rag_nano.components.embedding import MockEmbeddingProvider
from rag_nano.components.retriever import CosineTopKRetriever
from rag_nano.components.reranker import IdentityReranker
from rag_nano.core.retrieval import Components, retrieve
from rag_nano.types import RetrievalQuery


class TestProvenanceInvariant:
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

    def test_100_random_queries_all_hits_attributed(self, components) -> None:
        queries = [
            "BGE-m3 prefix",
            "hotfix deploy",
            "incident response",
            "librarian design",
            "markdown chunker",
            "E5 model",
            "smoke test",
            "HTTP contract",
            "char chunker",
            "system architecture",
        ]
        rng = random.Random(42)
        for _ in range(100):
            q = rng.choice(queries)
            query = RetrievalQuery(query=q, k=5)
            resp = retrieve(query, components)
            for r in resp.results:
                assert r.chunk_id, "missing chunk_id"
                assert r.source_id, "missing source_id"
                assert r.source_path, "missing source_path"
                assert isinstance(r.score, float), "missing or bad score"
                assert r.data_type, "missing data_type"
                assert r.category is not None, "missing category"
                assert r.text, "missing text"
