import pytest

from rag_nano.components.structured_store import InMemoryStructuredStore
from rag_nano.components.vector_store import InMemoryVectorStore
from rag_nano.config import Settings
from rag_nano.core.ingest import ingest


class TestIngestPipeline:
    @pytest.fixture
    def stores(self):
        return InMemoryStructuredStore(), InMemoryVectorStore()

    @pytest.fixture
    def settings(self):
        return Settings(
            embedding_backend="mock", vector_store="in_memory", structured_store="in_memory"
        )

    def test_valid_items_become_retrievable(self, stores, settings) -> None:
        structured, vector = stores
        paths = [
            p
            for p in (pytest.importorskip("pathlib").Path("tests/fixtures/seed_corpus")).iterdir()
            if p.suffix in (".md", ".py") and "credential" not in p.name and p.suffix != ".log"
        ]
        if not paths:
            pytest.skip("No valid seed corpus files")
        report = ingest(paths, structured, vector, settings)
        assert report.accepted >= 1
        assert report.total_chunks >= 1

    def test_cold_and_credential_rejected(self, stores, settings) -> None:
        structured, vector = stores
        corpus = pytest.importorskip("pathlib").Path("tests/fixtures/seed_corpus")
        paths = list(corpus.glob("*.log")) + list(corpus.glob("*credential*"))
        if not paths:
            pytest.skip("No cold/credential seed files")
        report = ingest(paths, structured, vector, settings)
        assert report.rejected == len(paths)

    def test_reingest_noop(self, stores, settings) -> None:
        structured, vector = stores
        corpus = pytest.importorskip("pathlib").Path("tests/fixtures/seed_corpus")
        md_files = list(corpus.glob("faq_embedding_zh.md"))
        if not md_files:
            pytest.skip("No faq seed file")
        report1 = ingest(md_files, structured, vector, settings)
        initial_chunks = report1.total_chunks
        report2 = ingest(md_files, structured, vector, settings)
        assert report2.accepted == 0  # no-op
        stats = structured.get_stats()
        assert stats["chunk_count"] == initial_chunks

    def test_run_report_has_counts(self, stores, settings) -> None:
        structured, vector = stores
        corpus = pytest.importorskip("pathlib").Path("tests/fixtures/seed_corpus")
        paths = list(corpus.iterdir())
        report = ingest(paths, structured, vector, settings)
        assert report.accepted + report.rejected > 0
        assert report.total_chunks >= 0
        assert isinstance(report.by_data_type, dict)
