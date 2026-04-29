from datetime import UTC, datetime

import pytest

from rag_nano.components.structured_store import SqliteStructuredStore
from rag_nano.types import DataType, KnowledgeChunk, KnowledgeSource


class TestSqliteStructuredStore:
    @pytest.fixture
    def store(self, tmp_path):
        return SqliteStructuredStore(tmp_path / "test.db")

    def test_schema_idempotent(self, store) -> None:
        # Connecting twice should not raise
        store._connect()
        store._connect()
        assert store._conn is not None

    def test_wal_mode_active(self, store) -> None:
        conn = store._connect()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"

    def test_insert_and_query_source(self, store) -> None:
        source = KnowledgeSource(
            source_id="s1",
            source_path="/faq/q1.md",
            data_type=DataType.faq,
            category="ops",
            content_hash="abc123",
            ingested_at=datetime.now(UTC),
            chunk_count=1,
        )
        store.insert_source(source)
        fetched = store.get_source("s1")
        assert fetched is not None
        assert fetched.source_path == "/faq/q1.md"

    def test_unique_path_hash_blocks_duplicate(self, store) -> None:
        source = KnowledgeSource(
            source_id="s1",
            source_path="/faq/q1.md",
            data_type=DataType.faq,
            category="ops",
            content_hash="abc123",
            ingested_at=datetime.now(UTC),
            chunk_count=1,
        )
        store.insert_source(source)
        # Same path + hash → replace (no error)
        source2 = KnowledgeSource(
            source_id="s2",
            source_path="/faq/q1.md",
            data_type=DataType.faq,
            category="ops",
            content_hash="abc123",
            ingested_at=datetime.now(UTC),
            chunk_count=2,
        )
        store.insert_source(source2)
        fetched = store.get_source_by_path_and_hash("/faq/q1.md", "abc123")
        assert fetched is not None
        assert fetched.chunk_count == 2

    def test_cascade_delete(self, store) -> None:
        source = KnowledgeSource(
            source_id="s1",
            source_path="/faq/q1.md",
            data_type=DataType.faq,
            category="ops",
            content_hash="abc123",
            ingested_at=datetime.now(UTC),
            chunk_count=1,
        )
        chunk = KnowledgeChunk(
            chunk_id="c1",
            source_id="s1",
            text="hello",
            position=0,
            embedding_index=0,
            data_type=DataType.faq,
            category="ops",
        )
        store.insert_source(source)
        store.insert_chunks([chunk])

        store.delete_source("s1")
        chunks = store.query_chunks(chunk_ids=["c1"])
        assert chunks == []

    def test_query_chunks_by_data_type(self, store) -> None:
        source = KnowledgeSource(
            source_id="s1",
            source_path="/faq/q1.md",
            data_type=DataType.faq,
            category="ops",
            content_hash="abc123",
            ingested_at=datetime.now(UTC),
            chunk_count=2,
        )
        chunks = [
            KnowledgeChunk(
                chunk_id="c1",
                source_id="s1",
                text="faq text",
                position=0,
                embedding_index=0,
                data_type=DataType.faq,
                category="ops",
            ),
            KnowledgeChunk(
                chunk_id="c2",
                source_id="s1",
                text="sop text",
                position=1,
                embedding_index=1,
                data_type=DataType.sop,
                category="ops",
            ),
        ]
        store.insert_source(source)
        store.insert_chunks(chunks)

        faq_chunks = store.query_chunks(data_types=["faq"])
        assert len(faq_chunks) == 1
        assert faq_chunks[0].chunk_id == "c1"
