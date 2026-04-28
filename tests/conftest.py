from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from rag_nano.components.embedding import MockEmbeddingProvider
from rag_nano.components.retriever import CosineTopKRetriever
from rag_nano.components.reranker import IdentityReranker
from rag_nano.components.structured_store import InMemoryStructuredStore
from rag_nano.components.vector_store import InMemoryVectorStore
from rag_nano.config import Settings
from rag_nano.core.retrieval import Components
from rag_nano.types import DataType, KnowledgeChunk, KnowledgeSource


@pytest.fixture
def tmp_index_dir(tmp_path: Path) -> Path:
    d = tmp_path / "index"
    d.mkdir()
    return d


@pytest.fixture
def mock_settings(tmp_index_dir: Path) -> Settings:
    return Settings(
        index_dir=tmp_index_dir,
        embedding_backend="mock",
        vector_store="in_memory",
        structured_store="in_memory",
        reranker="identity",
    )


@pytest.fixture
def seed_index_fixture(mock_settings: Settings) -> tuple[InMemoryStructuredStore, InMemoryVectorStore]:
    """Direct-write seed fixture bypassing the ingest pipeline.

    Returns (structured_store, vector_store) pre-populated with a small
    mix of faq, sop, wiki, and code_summary chunks.
    """
    structured = InMemoryStructuredStore()
    vector = InMemoryVectorStore()
    embed = MockEmbeddingProvider(dim=4)

    corpus = [
        ("faq/embedding.md", DataType.faq, "embedding", ["BGE-m3 prefix config", "E5 model options"]),
        ("faq/deploy.md", DataType.faq, "ops", ["hotfix branch strategy", "smoke test checklist"]),
        ("sop/incident.md", DataType.sop, "ops", ["incident response step 1", "incident response step 2"]),
        ("wiki/arch.md", DataType.wiki, "system", ["librarian decoupled design", "HTTP contract stable"]),
        ("code/chunker.py", DataType.code_summary, "ingest", ["markdown chunker util", "char chunker util"]),
    ]

    emb_idx = 0
    for path, dtype, category, chunk_texts in corpus:
        source_id = _ulid_from_text(path)
        content = "\n".join(chunk_texts)
        source = KnowledgeSource(
            source_id=source_id,
            source_path=path,
            data_type=dtype,
            category=category,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            ingested_at=datetime.now(timezone.utc),
            chunk_count=len(chunk_texts),
        )
        structured.insert_source(source)

        embs = embed.encode(chunk_texts)
        chunk_ids = []
        chunks = []
        for pos, text in enumerate(chunk_texts):
            cid = _ulid_from_text(f"{path}:{pos}")
            chunk_ids.append(cid)
            chunks.append(
                KnowledgeChunk(
                    chunk_id=cid,
                    source_id=source_id,
                    text=text,
                    position=pos,
                    embedding_index=emb_idx + pos,
                    data_type=dtype,
                    category=category,
                )
            )
        structured.insert_chunks(chunks)
        vector.add(chunk_ids, embs)
        emb_idx += len(chunk_texts)

    return structured, vector


def _ulid_from_text(text: str) -> str:
    """Deterministic pseudo-ULID for test fixtures."""
    h = hashlib.sha256(text.encode()).hexdigest()[:26]
    return f"01{h}"


@pytest.fixture
def app_fixture(mock_settings: Settings, seed_index_fixture) -> "FastAPI":
    """FastAPI app wired with seeded in-memory stores."""
    from fastapi import FastAPI

    from rag_nano.api.app import create_app

    structured, vector = seed_index_fixture
    app = create_app(mock_settings)
    app.state.components = Components(
        embedding_provider=MockEmbeddingProvider(dim=4),
        vector_store=vector,
        retriever=CosineTopKRetriever(),
        reranker=IdentityReranker(),
        structured_store=structured,
    )
    return app


@pytest.fixture
def app_empty_fixture(mock_settings: Settings) -> "FastAPI":
    """FastAPI app with empty stores."""
    from rag_nano.api.app import create_app

    return create_app(mock_settings)


@pytest.fixture
def seed_index_via_ingest_fixture(mock_settings: Settings) -> tuple[InMemoryStructuredStore, InMemoryVectorStore]:
    """Seed fixture using the real ingest pipeline on the seed corpus.

    Returns (structured_store, vector_store) populated via rag_nano.core.ingest.ingest().
    """
    from rag_nano.core.ingest import ingest

    structured = InMemoryStructuredStore()
    vector = InMemoryVectorStore()

    corpus_root = Path(__file__).parent / "fixtures" / "seed_corpus"
    if not corpus_root.exists():
        pytest.skip("seed_corpus not found")

    paths = [p for p in corpus_root.iterdir() if p.is_file()]
    ingest(paths, structured, vector, mock_settings)
    return structured, vector
