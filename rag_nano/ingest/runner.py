from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ulid import ULID

from rag_nano.config import Settings
from rag_nano.ingest.chunker import chunk
from rag_nano.ingest.credential_scan import scan as credential_scan
from rag_nano.ingest.value_gate import (
    evaluate,
)
from rag_nano.types import (
    KnowledgeChunk,
    KnowledgeSource,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    source: KnowledgeSource | None
    chunks: list[KnowledgeChunk]
    rejected: str | None


def run_pipeline(
    item: Any, structured_store: Any, settings: Settings, embedding_provider: Any, vector_store: Any
) -> PipelineResult:
    source_id = str(ULID())
    path = item.source_path
    content = item.content
    original_metadata = item.original_metadata
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    # Value gate
    data_type, rejection = evaluate(item, structured_store)
    if rejection:
        return PipelineResult(source=None, chunks=[], rejected=rejection)

    # Credential scan on each chunk after chunking
    text_chunks = chunk(content, data_type.value)
    for text in text_chunks:
        cred = credential_scan(text)
        if cred:
            return PipelineResult(source=None, chunks=[], rejected=cred)

    # Dedup: check if existing source with same path+hash
    existing = structured_store.get_source_by_path_and_hash(path, content_hash)
    if existing:
        return PipelineResult(source=None, chunks=[], rejected="cold_data_duplicate")

    # Category from metadata or parent dir
    category = original_metadata.get("category", "")
    if not category:
        p = Path(path)
        category = p.parts[-2] if len(p.parts) >= 2 else p.stem

    ingested_at = datetime.now(UTC)
    source = KnowledgeSource(
        source_id=source_id,
        source_path=path,
        data_type=data_type,
        category=category,
        content_hash=content_hash,
        ingested_at=ingested_at,
        chunk_count=len(text_chunks),
        original_metadata=original_metadata,
    )

    # Embed chunks
    embeddings = embedding_provider.encode(text_chunks, task="passage")

    # Build chunk records with embedding indices
    chunks: list[KnowledgeChunk] = []
    for pos, (text, emb) in enumerate(zip(text_chunks, embeddings, strict=False)):
        chunk_id = str(ULID())
        emb_idx = int(vector_store.count())
        chunks.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                source_id=source_id,
                text=text,
                position=pos,
                embedding_index=emb_idx,
                data_type=data_type,
                category=category,
                original_metadata=original_metadata,
            )
        )
        vector_store.add([chunk_id], emb.reshape(1, -1))

    return PipelineResult(source=source, chunks=chunks, rejected=None)


def commit_source(result: PipelineResult, structured_store: Any, settings: Settings) -> None:
    if result.source is None:
        return
    # Check for existing source with same path (replace on content change)
    existing = structured_store.get_source_by_path_and_hash(
        result.source.source_path, result.source.content_hash
    )
    if existing:
        # Already handled in run_pipeline - should not reach here
        return
    structured_store.insert_source(result.source)
    structured_store.insert_chunks(result.chunks)
