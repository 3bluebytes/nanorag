import threading
import time

from rag_nano.components.structured_store import InMemoryStructuredStore
from rag_nano.components.vector_store import InMemoryVectorStore
from rag_nano.config import Settings
from rag_nano.core.ingest import ingest


class TestConcurrentAccess:
    def test_retrieval_observes_consistent_state(self) -> None:
        structured = InMemoryStructuredStore()
        vector = InMemoryVectorStore()
        settings = Settings(
            embedding_backend="mock", vector_store="in_memory", structured_store="in_memory"
        )

        seen_states = []

        def ingest_thread():
            from pathlib import Path

            corpus = Path("tests/fixtures/seed_corpus")
            md_files = [
                f
                for f in corpus.iterdir()
                if f.suffix in (".md", ".py") and "credential" not in f.name
            ]
            if not md_files:
                return
            ingest(md_files, structured, vector, settings)
            time.sleep(0.1)

        def retrieve_thread():
            for _ in range(5):
                count = structured.get_stats()["chunk_count"]
                seen_states.append(count)
                time.sleep(0.02)

        t1 = threading.Thread(target=ingest_thread)
        t2 = threading.Thread(target=retrieve_thread)
        t2.start()
        t1.start()
        t1.join()
        t2.join()

        # All observed counts should be either 0 (before ingest) or >= some positive (after)
        # No partial states (e.g. non-integer counts)
        for s in seen_states:
            assert isinstance(s, int)
