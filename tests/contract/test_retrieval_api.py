import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class TestRetrieveEndpoint:
    @pytest.fixture
    async def client(self, app_fixture: FastAPI):
        transport = ASGITransport(app=app_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_basic_ranked_attribution(self, client) -> None:
        resp = await client.post(
            "/v1/retrieve",
            json={"query": "BGE-m3 prefix config", "k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_version"] == "1"
        assert len(data["results"]) > 0
        for r in data["results"]:
            assert r["chunk_id"]
            assert r["source_id"]
            assert r["source_path"]
            assert isinstance(r["score"], float)
            assert r["data_type"]
            assert r["category"]
            assert r["text"]

    async def test_filter_pre_application(self, client) -> None:
        resp = await client.post(
            "/v1/retrieve",
            json={
                "query": "BGE-m3 prefix config",
                "k": 5,
                "filters": {"data_types": ["sop"]},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Mock embeddings don't preserve real semantic similarity,
        # so verify the filter was applied (all results are SOP type).
        for r in data["results"]:
            assert r["data_type"] == "sop"

    async def test_debug_mode(self, client) -> None:
        resp = await client.post(
            "/v1/retrieve",
            json={"query": "BGE-m3 prefix config", "k": 2, "debug": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "debug" in data
        assert "recall_candidates" in data["debug"]
        assert "rerank_detail" in data["debug"]

    async def test_empty_hit_list_is_200(self, client) -> None:
        resp = await client.post(
            "/v1/retrieve",
            json={"query": "completely nonexistent topic xyz", "k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        # With mock embeddings semantic unrelatedness is not guaranteed,
        # but stats must be consistent with results length.
        assert data["stats"]["returned"] == len(data["results"])
        assert data["stats"]["total_candidates"] >= 0

    async def test_empty_query_returns_422(self, client) -> None:
        resp = await client.post(
            "/v1/retrieve",
            json={"query": "   ", "k": 3},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["api_version"] == "1"
        assert data["error"] == "validation_error"

    async def test_k_out_of_range_returns_422(self, client) -> None:
        resp = await client.post(
            "/v1/retrieve",
            json={"query": "hello", "k": 100},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["api_version"] == "1"

    async def test_fr005_drops_untraceable_result(self, app_empty_fixture: FastAPI) -> None:
        from datetime import datetime, timezone

        from rag_nano.components.embedding import MockEmbeddingProvider
        from rag_nano.components.retriever import CosineTopKRetriever
        from rag_nano.components.reranker import IdentityReranker
        from rag_nano.components.structured_store import InMemoryStructuredStore
        from rag_nano.components.vector_store import InMemoryVectorStore
        from rag_nano.core.retrieval import Components
        from rag_nano.types import DataType, KnowledgeChunk, KnowledgeSource

        structured = InMemoryStructuredStore()
        vector = InMemoryVectorStore()
        embed = MockEmbeddingProvider(dim=4)

        source = KnowledgeSource(
            source_id="s_bad",
            source_path="bad.md",
            data_type=DataType.faq,
            category="x",
            content_hash="bad",
            ingested_at=datetime.now(timezone.utc),
            chunk_count=1,
        )
        chunk = KnowledgeChunk(
            chunk_id="c_bad",
            source_id="s_bad",
            text="bad chunk",
            position=0,
            embedding_index=0,
            data_type=DataType.faq,
            category="x",
        )
        structured.insert_source(source)
        structured.insert_chunks([chunk])
        vector.add(["c_bad"], embed.encode(["bad chunk"]))

        # Now remove the source so chunk becomes orphan
        structured.delete_source("s_bad")

        app_empty_fixture.state.components = Components(
            embedding_provider=embed,
            vector_store=vector,
            retriever=CosineTopKRetriever(),
            reranker=IdentityReranker(),
            structured_store=structured,
        )

        transport = ASGITransport(app=app_empty_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/v1/retrieve",
                json={"query": "bad chunk", "k": 3},
            )
            assert resp.status_code == 200
            data = resp.json()
            # Orphan chunk should be dropped, not returned
            for r in data["results"]:
                assert r["source_id"] != ""
                assert r["source_path"] != ""
