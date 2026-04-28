from rag_nano.components.reranker import IdentityReranker
from rag_nano.types import DataType, RetrievalResultRecord


class TestIdentityReranker:
    def test_preserves_order(self) -> None:
        r = IdentityReranker()
        results = [
            RetrievalResultRecord(
                chunk_id="c1",
                source_id="s1",
                source_path="a.md",
                score=0.9,
                data_type=DataType.faq,
                category="x",
                text="t1",
            ),
            RetrievalResultRecord(
                chunk_id="c2",
                source_id="s1",
                source_path="a.md",
                score=0.8,
                data_type=DataType.faq,
                category="x",
                text="t2",
            ),
        ]
        reranked, detail = r.rerank(results, "q")
        assert [x.chunk_id for x in reranked] == ["c1", "c2"]

    def test_emits_identity_explanation(self) -> None:
        r = IdentityReranker()
        results = [
            RetrievalResultRecord(
                chunk_id="c1",
                source_id="s1",
                source_path="a.md",
                score=0.9,
                data_type=DataType.faq,
                category="x",
                text="t1",
            ),
        ]
        _, detail = r.rerank(results, "q")
        assert len(detail) == 1
        assert detail[0]["rerank_explanation"] == "identity"
        assert detail[0]["pre_rank_score"] == detail[0]["post_rank_score"]
