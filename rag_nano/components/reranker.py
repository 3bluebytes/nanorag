from __future__ import annotations

from typing import Any

from rag_nano.types import RetrievalResultRecord


class IdentityReranker:
    def rerank(
        self, results: list[RetrievalResultRecord], query: str
    ) -> tuple[list[RetrievalResultRecord], list[dict]]:
        detail = [
            {
                "chunk_id": r.chunk_id,
                "pre_rank_score": r.score,
                "post_rank_score": r.score,
                "rerank_explanation": "identity",
            }
            for r in results
        ]
        return list(results), detail


class MockReranker:
    def __init__(self, reverse: bool = False) -> None:
        self.reverse = reverse

    def rerank(
        self, results: list[RetrievalResultRecord], query: str
    ) -> tuple[list[RetrievalResultRecord], list[dict]]:
        ordered = list(reversed(results)) if self.reverse else list(results)
        detail = [
            {
                "chunk_id": r.chunk_id,
                "pre_rank_score": r.score,
                "post_rank_score": r.score,
                "rerank_explanation": "mock",
            }
            for r in ordered
        ]
        return ordered, detail


def get_reranker(settings: Any) -> Any:
    if settings.reranker == "identity":
        return IdentityReranker()
    raise ValueError(f"Unknown reranker: {settings.reranker}")
