from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from rag_nano.config import Settings
from rag_nano.types import KnowledgeChunk, KnowledgeSource

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_source (
  source_id        TEXT PRIMARY KEY,
  source_path      TEXT NOT NULL,
  data_type        TEXT NOT NULL,
  category         TEXT NOT NULL,
  content_hash     TEXT NOT NULL,
  ingested_at      TEXT NOT NULL,
  chunk_count      INTEGER NOT NULL,
  original_metadata_json TEXT NOT NULL,
  UNIQUE (source_path, content_hash)
);

CREATE TABLE IF NOT EXISTS knowledge_chunk (
  chunk_id         TEXT PRIMARY KEY,
  source_id        TEXT NOT NULL REFERENCES knowledge_source(source_id) ON DELETE CASCADE,
  text             TEXT NOT NULL,
  position         INTEGER NOT NULL,
  embedding_index  INTEGER NOT NULL UNIQUE,
  data_type        TEXT NOT NULL,
  category         TEXT NOT NULL,
  original_metadata_json TEXT NOT NULL,
  UNIQUE (source_id, position)
);

CREATE INDEX IF NOT EXISTS idx_chunk_data_type ON knowledge_chunk(data_type);
CREATE INDEX IF NOT EXISTS idx_chunk_category  ON knowledge_chunk(category);
"""


class SqliteStructuredStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA_SQL)
            self._conn.commit()
        return self._conn

    def insert_source(self, source: KnowledgeSource) -> None:
        conn = self._connect()
        conn.execute(
            """
            INSERT OR REPLACE INTO knowledge_source
            (source_id, source_path, data_type, category, content_hash, ingested_at, chunk_count, original_metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.source_id,
                source.source_path,
                source.data_type.value,
                source.category,
                source.content_hash,
                source.ingested_at.isoformat(),
                source.chunk_count,
                json.dumps(source.original_metadata, ensure_ascii=False),
            ),
        )
        conn.commit()

    def insert_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        conn = self._connect()
        conn.executemany(
            """
            INSERT OR REPLACE INTO knowledge_chunk
            (chunk_id, source_id, text, position, embedding_index, data_type, category, original_metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    c.chunk_id,
                    c.source_id,
                    c.text,
                    c.position,
                    c.embedding_index,
                    c.data_type.value,
                    c.category,
                    json.dumps(c.original_metadata, ensure_ascii=False),
                )
                for c in chunks
            ],
        )
        conn.commit()

    def query_chunks(
        self,
        data_types: list[str] | None = None,
        categories: list[str] | None = None,
        chunk_ids: list[str] | None = None,
    ) -> list[KnowledgeChunk]:
        conn = self._connect()
        where_clauses: list[str] = []
        params: list[Any] = []
        if data_types:
            placeholders = ", ".join("?" * len(data_types))
            where_clauses.append(f"data_type IN ({placeholders})")
            params.extend(data_types)
        if categories:
            placeholders = ", ".join("?" * len(categories))
            where_clauses.append(f"category IN ({placeholders})")
            params.extend(categories)
        if chunk_ids:
            placeholders = ", ".join("?" * len(chunk_ids))
            where_clauses.append(f"chunk_id IN ({placeholders})")
            params.extend(chunk_ids)

        sql = "SELECT * FROM knowledge_chunk"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        rows = conn.execute(sql, params).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM knowledge_chunk").description]
        return [_row_to_chunk(dict(zip(cols, r))) for r in rows]

    def get_source(self, source_id: str) -> KnowledgeSource | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM knowledge_source WHERE source_id = ?", (source_id,)
        ).fetchone()
        if row is None:
            return None
        cols = [d[0] for d in conn.execute("SELECT * FROM knowledge_source").description]
        return _row_to_source(dict(zip(cols, row)))

    def get_source_by_path_and_hash(
        self, source_path: str, content_hash: str
    ) -> KnowledgeSource | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM knowledge_source WHERE source_path = ? AND content_hash = ?",
            (source_path, content_hash),
        ).fetchone()
        if row is None:
            return None
        cols = [d[0] for d in conn.execute("SELECT * FROM knowledge_source").description]
        return _row_to_source(dict(zip(cols, row)))

    def delete_source(self, source_id: str) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM knowledge_source WHERE source_id = ?", (source_id,))
        conn.commit()

    def wipe(self) -> None:
        conn = self._connect()
        conn.execute("DROP TABLE IF EXISTS knowledge_chunk")
        conn.execute("DROP TABLE IF EXISTS knowledge_source")
        conn.executescript(_SCHEMA_SQL)
        conn.commit()

    def get_stats(self) -> dict[str, Any]:
        conn = self._connect()
        chunk_count = conn.execute("SELECT COUNT(*) FROM knowledge_chunk").fetchone()[0]
        source_count = conn.execute("SELECT COUNT(*) FROM knowledge_source").fetchone()[0]
        by_data_type: dict[str, int] = {}
        for row in conn.execute(
            "SELECT data_type, COUNT(*) FROM knowledge_chunk GROUP BY data_type"
        ):
            by_data_type[row[0]] = row[1]
        last_ingest = conn.execute(
            "SELECT MAX(ingested_at) FROM knowledge_source"
        ).fetchone()[0]
        return {
            "chunk_count": chunk_count,
            "source_count": source_count,
            "by_data_type": by_data_type,
            "last_ingest_at": last_ingest,
        }


class InMemoryStructuredStore:
    def __init__(self) -> None:
        self._sources: dict[str, KnowledgeSource] = {}
        self._chunks: dict[str, KnowledgeChunk] = {}

    def insert_source(self, source: KnowledgeSource) -> None:
        self._sources[source.source_id] = source

    def insert_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        for c in chunks:
            self._chunks[c.chunk_id] = c

    def query_chunks(
        self,
        data_types: list[str] | None = None,
        categories: list[str] | None = None,
        chunk_ids: list[str] | None = None,
    ) -> list[KnowledgeChunk]:
        results = list(self._chunks.values())
        if data_types:
            results = [c for c in results if c.data_type.value in data_types]
        if categories:
            results = [c for c in results if c.category in categories]
        if chunk_ids:
            s = set(chunk_ids)
            results = [c for c in results if c.chunk_id in s]
        return results

    def get_source(self, source_id: str) -> KnowledgeSource | None:
        return self._sources.get(source_id)

    def get_source_by_path_and_hash(
        self, source_path: str, content_hash: str
    ) -> KnowledgeSource | None:
        for s in self._sources.values():
            if s.source_path == source_path and s.content_hash == content_hash:
                return s
        return None

    def delete_source(self, source_id: str) -> None:
        self._sources.pop(source_id, None)
        self._chunks = {
            cid: c for cid, c in self._chunks.items() if c.source_id != source_id
        }

    def wipe(self) -> None:
        self._sources.clear()
        self._chunks.clear()

    def get_stats(self) -> dict[str, Any]:
        by_data_type: dict[str, int] = {}
        for c in self._chunks.values():
            by_data_type[c.data_type.value] = by_data_type.get(c.data_type.value, 0) + 1
        last_ingest = None
        if self._sources:
            last_ingest = max(s.ingested_at.isoformat() for s in self._sources.values())
        return {
            "chunk_count": len(self._chunks),
            "source_count": len(self._sources),
            "by_data_type": by_data_type,
            "last_ingest_at": last_ingest,
        }


def _row_to_source(row: dict[str, Any]) -> KnowledgeSource:
    from datetime import datetime
    from rag_nano.types import DataType

    return KnowledgeSource(
        source_id=row["source_id"],
        source_path=row["source_path"],
        data_type=DataType(row["data_type"]),
        category=row["category"],
        content_hash=row["content_hash"],
        ingested_at=datetime.fromisoformat(row["ingested_at"]),
        chunk_count=row["chunk_count"],
        original_metadata=json.loads(row["original_metadata_json"]),
    )


def _row_to_chunk(row: dict[str, Any]) -> KnowledgeChunk:
    from rag_nano.types import DataType

    return KnowledgeChunk(
        chunk_id=row["chunk_id"],
        source_id=row["source_id"],
        text=row["text"],
        position=row["position"],
        embedding_index=row["embedding_index"],
        data_type=DataType(row["data_type"]),
        category=row["category"],
        original_metadata=json.loads(row["original_metadata_json"]),
    )


def get_structured_store(settings: Settings) -> Any:
    if settings.structured_store == "sqlite":
        db_path = settings.index_dir / "structured.db"
        return SqliteStructuredStore(db_path)
    if settings.structured_store == "in_memory":
        return InMemoryStructuredStore()
    raise ValueError(f"Unknown structured store: {settings.structured_store}")
