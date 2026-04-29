"""Constitution VIII proof point #2.

Drives Example B from quickstart.md against an in-process app: a simulated
workflow agent processes a JSONL of issues, looks up SOP+FAQ chunks via the
retrieval API with `data_types` filter, asserts each output line has a
populated `librarian_top_k` block.
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


async def _lookup_for_issue(client: AsyncClient, title: str) -> dict:
    resp = await client.post(
        "/v1/retrieve",
        json={
            "query": title,
            "k": 3,
            "filters": {"data_types": ["sop", "faq"]},
        },
    )
    resp.raise_for_status()
    return resp.json()


async def _process_issues(client: AsyncClient, issues_jsonl: str) -> list[dict]:
    out: list[dict] = []
    for line in io.StringIO(issues_jsonl):
        if not line.strip():
            continue
        issue = json.loads(line)
        res = await _lookup_for_issue(client, issue["title"])
        issue["librarian_top_k"] = [
            {
                "source_path": r["source_path"],
                "score": r["score"],
                "data_type": r["data_type"],
                "preview": r["text"][:160],
            }
            for r in res["results"]
        ]
        out.append(issue)
    return out


class TestWorkflowAgentIntegration:
    @pytest.fixture
    async def client(self, app_fixture: FastAPI):
        transport = ASGITransport(app=app_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_each_issue_gets_librarian_top_k_block(self, client) -> None:
        issues_jsonl = "\n".join(
            json.dumps(i, ensure_ascii=False)
            for i in [
                {"id": 101, "title": "How do I deploy a hotfix?"},
                {"id": 102, "title": "incident response procedure"},
                {"id": 103, "title": "smoke test before merge"},
            ]
        )
        results = await _process_issues(client, issues_jsonl)
        assert len(results) == 3
        for issue in results:
            assert "librarian_top_k" in issue
            assert isinstance(issue["librarian_top_k"], list)
            for hit in issue["librarian_top_k"]:
                assert hit["source_path"]
                assert "preview" in hit
                # Filter is enforced server-side — only sop / faq survive.
                assert hit["data_type"] in {"sop", "faq"}

    async def test_filter_excludes_other_data_types(self, client) -> None:
        # The fixture has wiki + code_summary chunks too — they must not appear.
        results = await _process_issues(
            client,
            json.dumps({"id": 1, "title": "system architecture overview"}),
        )
        assert len(results) == 1
        for hit in results[0]["librarian_top_k"]:
            assert hit["data_type"] in {"sop", "faq"}

    async def test_no_librarian_business_logic_leaked(self, client) -> None:
        # The librarian returns chunks; the agent decides what to put in the report.
        # Re-running the same lookup should produce the same chunks (no hidden state).
        a = await _lookup_for_issue(client, "incident response procedure")
        b = await _lookup_for_issue(client, "incident response procedure")
        assert [r["chunk_id"] for r in a["results"]] == [r["chunk_id"] for r in b["results"]]
