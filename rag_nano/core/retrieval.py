from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from rag_nano.components.protocols import (
    EmbeddingProvider,
    Reranker,
    Retriever,
    StructuredStore,
    VectorStore,
)
from rag_nano.types import (
    RetrievalDebugDetail,
    RetrievalQuery,
    RetrievalResponse,
    RetrievalResultRecord,
    RetrievalStats,
    RerankDetailEntry,
)

logger = logging.getLogger(__name__)


@dataclass
class Components:
    embedding_provider: EmbeddingProvider
    vector_store: VectorStore
    retriever: Retriever
    reranker: Reranker
    structured_store: StructuredStore


def retrieve(query: RetrievalQuery, components: Components) -> RetrievalResponse:
    t0 = time.perf_counter()

    candidates = components.retriever.retrieve(
        query,
        components.embedding_provider,
        components.vector_store,
        components.structured_store,
    )

    reranked, rerank_detail = components.reranker.rerank(candidates, query.query)

    results: list[RetrievalResultRecord] = []
    for r in reranked:
        if not r.source_id or not r.source_path:
            logger.warning(
                "Dropping result with missing provenance",
                extra={"chunk_id": r.chunk_id, "source_id": r.source_id},
            )
            continue
        results.append(r)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    debug = None
    if query.debug:
        debug = RetrievalDebugDetail(
            recall_candidates=candidates,
            rerank_detail=[
                RerankDetailEntry(
                    chunk_id=d["chunk_id"],
                    pre_rank_score=d["pre_rank_score"],
                    post_rank_score=d["post_rank_score"],
                    rerank_explanation=d["rerank_explanation"],
                )
                for d in rerank_detail
            ],
        )

    return RetrievalResponse(
        query=query.query,
        k=query.k,
        results=results,
        stats=RetrievalStats(
            total_candidates=len(candidates),
            returned=len(results),
            elapsed_ms=elapsed_ms,
        ),
        debug=debug,
    )
