import contextlib
from unittest.mock import MagicMock, patch

from rag_nano.components.structured_store import InMemoryStructuredStore
from rag_nano.components.vector_store import InMemoryVectorStore
from rag_nano.config import Settings
from rag_nano.ingest.loaders import RawItem
from rag_nano.ingest.runner import run_pipeline


class TestAtomicFailureRollback:
    def test_embedding_failure_leaves_no_partial_state(self) -> None:
        structured = InMemoryStructuredStore()
        vector = InMemoryVectorStore()
        settings = Settings(
            embedding_backend="mock", vector_store="in_memory", structured_store="in_memory"
        )

        bad_item = RawItem(
            source_path="/test/bad.md",
            content="# Bad\ncontent",
            original_metadata={},
        )

        with (
            patch.object(settings, "embedding_backend", "nonexistent"),
            contextlib.suppress(Exception),
        ):
            run_pipeline(bad_item, structured, settings, MagicMock(), vector)

        stats = structured.get_stats()
        assert stats["chunk_count"] == 0
        assert stats["source_count"] == 0
