from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from rag_nano.api.models import (
    DebugBlock,
    ErrorResponse,
    HealthResponse,
    IndexStatsResponse,
    RerankDetailItem,
    ResultItem,
    RetrieveRequest,
    RetrieveResponse,
    StatsBlock,
)
from rag_nano.core.retrieval import Components, retrieve
from rag_nano.types import RetrievalFilters, RetrievalQuery, RetrievalResultRecord

router = APIRouter()


def _get_components(request: Request) -> Components:
    return request.app.state.components


def _result_item(r: RetrievalResultRecord) -> ResultItem:
    return ResultItem(
        chunk_id=r.chunk_id,
        source_id=r.source_id,
        source_path=r.source_path,
        score=r.score,
        data_type=r.data_type.value,
        category=r.category,
        text=r.text,
        original_metadata=r.original_metadata,
    )


@router.post("/v1/retrieve", response_model=RetrieveResponse)
async def post_retrieve(
    body: RetrieveRequest,
    components: Components = Depends(_get_components),
) -> RetrieveResponse:
    query = RetrievalQuery(
        query=body.query,
        k=body.k,
        filters=RetrievalFilters(
            data_types=list(body.filters.data_types),
            categories=list(body.filters.categories),
        ),
        debug=body.debug,
    )
    response = retrieve(query, components)

    debug_block: DebugBlock | None = None
    if response.debug is not None:
        debug_block = DebugBlock(
            recall_candidates=[_result_item(r) for r in response.debug.recall_candidates],
            rerank_detail=[
                RerankDetailItem(
                    chunk_id=d.chunk_id,
                    pre_rank_score=d.pre_rank_score,
                    post_rank_score=d.post_rank_score,
                    rerank_explanation=d.rerank_explanation,
                )
                for d in response.debug.rerank_detail
            ],
        )

    return RetrieveResponse(
        query=response.query,
        k=response.k,
        results=[_result_item(r) for r in response.results],
        stats=StatsBlock(
            total_candidates=response.stats.total_candidates,
            returned=response.stats.returned,
            elapsed_ms=response.stats.elapsed_ms,
        ),
        debug=debug_block,
    )


@router.get("/v1/health", response_model=HealthResponse)
async def get_health(
    request: Request,
    components: Components = Depends(_get_components),
) -> HealthResponse:
    index_loaded = components.structured_store.get_stats()["chunk_count"] > 0
    settings = request.app.state.settings
    model = settings.embedding_model if settings else "unknown"
    if index_loaded:
        return HealthResponse(
            status="ok",
            index_loaded=True,
            embedding_model=model,
        )
    return HealthResponse(
        status="degraded",
        index_loaded=False,
        embedding_model=model,
        detail="no chunks ingested yet",
    )


@router.get("/v1/index/stats", response_model=IndexStatsResponse)
async def get_index_stats(
    request: Request,
    components: Components = Depends(_get_components),
) -> IndexStatsResponse:
    stats = components.structured_store.get_stats()
    settings = request.app.state.settings
    model = settings.embedding_model if settings else "unknown"
    return IndexStatsResponse(
        chunk_count=stats.get("chunk_count", 0),
        source_count=stats.get("source_count", 0),
        by_data_type=stats.get("by_data_type", {}),
        embedding_model=model,
        embedding_dim=768,
        last_ingest_at=stats.get("last_ingest_at"),
        index_path=str(settings.index_dir) if settings else "",
    )


def validation_error_handler(request: Request, exc: Any) -> JSONResponse:
    errors = []
    if hasattr(exc, "errors"):
        for err in exc.errors():
            errors.append(
                {
                    "loc": err.get("loc", []),
                    "msg": err.get("msg", ""),
                    "type": err.get("type", ""),
                }
            )
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            detail=errors,
        ).model_dump(),
    )
