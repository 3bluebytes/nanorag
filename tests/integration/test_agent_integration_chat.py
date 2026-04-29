"""Constitution VIII proof point #1.

Drives Example A from quickstart.md against an in-process app: a simulated
chat agent posts a question, gets results, formats them with citations,
asserts the formatted answer carries source paths.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _render_for_chat(results: list[dict]) -> str:
    if not results:
        return "I don't have anything authoritative to cite on that."
    bullets = []
    for r in results:
        bullets.append(
            f"- {r['text'][:240]}…\n  source: {r['source_path']} ({r['data_type']}, score {r['score']:.2f})"
        )
    return "Here's what the knowledge base has, with sources:\n" + "\n".join(bullets)


class TestChatAgentIntegration:
    @pytest.fixture
    async def client(self, app_fixture: FastAPI):
        transport = ASGITransport(app=app_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_agent_posts_question_and_renders_with_citations(self, client) -> None:
        # Agent dispatches a query — no agent-side prompt logic in the librarian.
        resp = await client.post(
            "/v1/retrieve",
            json={"query": "incident response steps", "k": 3},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0

        # Agent owns the rendering; it must be able to surface attribution.
        rendered = _render_for_chat(results)
        for r in results:
            assert r["source_path"] in rendered
            assert r["data_type"] in rendered

    async def test_empty_results_path_renders_safely(self, app_empty_fixture) -> None:
        transport = ASGITransport(app=app_empty_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/v1/retrieve", json={"query": "anything", "k": 5})
        assert resp.status_code == 200
        rendered = _render_for_chat(resp.json()["results"])
        # The agent's UX gracefully handles "no authoritative answer".
        assert "don't have anything authoritative" in rendered

    async def test_every_rendered_hit_has_attribution(self, client) -> None:
        resp = await client.post(
            "/v1/retrieve",
            json={"query": "embedding model prefix convention", "k": 5},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        for r in results:
            assert r["source_id"]
            assert r["source_path"]
            assert r["chunk_id"]
            assert isinstance(r["score"], float)
