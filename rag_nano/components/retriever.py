from __future__ import annotations

import logging
from typing import Any

from rag_nano.components.protocols import (
    EmbeddingProvider,
    StructuredStore,
    VectorStore,
)
from rag_nano.types import (
    RetrievalQuery,
    RetrievalResultRecord,
)

logger = logging.getLogger(__name__)


class CosineTopKRetriever:
    def retrieve(
        self,
        query: RetrievalQuery,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        structured_store: StructuredStore,
    ) -> list[RetrievalResultRecord]:
        q_embedding = embedding_provider.encode([query.query], task="query")
        q_embedding = q_embedding[0]

        chunk_id_filter: set[str] | None = None
        if query.filters.data_types or query.filters.categories:
            chunks = structured_store.query_chunks(
                data_types=[dt.value for dt in query.filters.data_types] if query.filters.data_types else None,
                categories=query.filters.categories if query.filters.categories else None,
            )
            chunk_id_filter = {c.chunk_id for c in chunks}

        candidates = vector_store.search(q_embedding, query.k, chunk_id_filter)

        if not candidates:
            return []

        candidate_chunk_ids = [cid for cid, _ in candidates]
        chunk_records = structured_store.query_chunks(chunk_ids=candidate_chunk_ids)
        chunk_by_id = {c.chunk_id: c for c in chunk_records}

        results: list[RetrievalResultRecord] = []
        for chunk_id, score in candidates:
            chunk = chunk_by_id.get(chunk_id)
            if chunk is None:
                continue
            source = structured_store.get_source(chunk.source_id)
            if source is None:
                logger.warning(
                    "Dropping result with missing source",
                    extra={"chunk_id": chunk_id, "source_id": chunk.source_id},
                )
                continue
            results.append(
                RetrievalResultRecord(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    source_path=source.source_path,
                    score=score,
                    data_type=chunk.data_type,
                    category=chunk.category,
                    text=chunk.text,
                    original_metadata=chunk.original_metadata,
                )
            )
        return results


class MockRetriever:
    def __init__(self, fixed_results: list[RetrievalResultRecord] | None = None) -> None:
        self.fixed_results = fixed_results or []

    def retrieve(
        self,
        query: RetrievalQuery,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        structured_store: StructuredStore,
    ) -> list[RetrievalResultRecord]:
        return list(self.fixed_results)


def get_retriever(_settings: Any) -> Any:
    return CosineTopKRetriever()
