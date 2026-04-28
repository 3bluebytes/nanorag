import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class TestHealthEndpoint:
    @pytest.fixture
    async def client(self, app_fixture: FastAPI):
        transport = ASGITransport(app=app_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_health_ok_when_index_loaded(self, client) -> None:
        resp = await client.get("/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_version"] == "1"
        assert data["status"] == "ok"
        assert data["index_loaded"] is True

    async def test_health_degraded_when_empty(self, app_empty_fixture: FastAPI) -> None:
        transport = ASGITransport(app=app_empty_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["index_loaded"] is False
            assert "no chunks" in data["detail"]


class TestStatsEndpoint:
    @pytest.fixture
    async def client(self, app_fixture: FastAPI):
        transport = ASGITransport(app=app_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_stats_populated_when_seeded(self, client) -> None:
        resp = await client.get("/v1/index/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_version"] == "1"
        assert data["chunk_count"] > 0
        assert data["source_count"] > 0
        assert data["by_data_type"]
        assert isinstance(data["embedding_dim"], int)

    async def test_stats_empty_when_no_chunks(self, app_empty_fixture: FastAPI) -> None:
        transport = ASGITransport(app=app_empty_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/v1/index/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert data["chunk_count"] == 0
            assert data["source_count"] == 0
