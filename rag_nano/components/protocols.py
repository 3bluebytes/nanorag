from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from rag_nano.types import (
    KnowledgeChunk,
    KnowledgeSource,
    RetrievalQuery,
    RetrievalResultRecord,
)


class EmbeddingProvider(Protocol):
    def encode(self, texts: list[str], task: str = "passage") -> Any: ...


class VectorStore(Protocol):
    def add(self, chunk_ids: list[str], embeddings: Any) -> None: ...
    def search(
        self, query_embedding: Any, k: int, chunk_id_filter: set[str] | None = None
    ) -> list[tuple[str, float]]: ...
    def clear(self) -> None: ...
    def persist(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...
    def count(self) -> int: ...


class Retriever(Protocol):
    def retrieve(
        self,
        query: RetrievalQuery,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        structured_store: StructuredStore,
    ) -> list[RetrievalResultRecord]: ...


class Reranker(Protocol):
    def rerank(
        self, results: list[RetrievalResultRecord], query: str
    ) -> tuple[list[RetrievalResultRecord], list[dict]]: ...


class MetadataExtractor(Protocol):
    def extract(self, source_path: str, content: str) -> dict[str, str]: ...


class StructuredStore(Protocol):
    def insert_source(self, source: KnowledgeSource) -> None: ...
    def insert_chunks(self, chunks: list[KnowledgeChunk]) -> None: ...
    def query_chunks(
        self,
        data_types: list[str] | None = None,
        categories: list[str] | None = None,
        chunk_ids: list[str] | None = None,
    ) -> list[KnowledgeChunk]: ...
    def get_source(self, source_id: str) -> KnowledgeSource | None: ...
    def get_source_by_path_and_hash(
        self, source_path: str, content_hash: str
    ) -> KnowledgeSource | None: ...
    def delete_source(self, source_id: str) -> None: ...
    def wipe(self) -> None: ...
    def get_stats(self) -> dict[str, Any]: ...
