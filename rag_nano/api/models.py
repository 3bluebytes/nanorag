from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from rag_nano.types import DataType


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=50)
    filters: FilterBlock = Field(default_factory=lambda: FilterBlock())
    debug: bool = False

    @field_validator("query")
    @classmethod
    def query_not_whitespace_only(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("query cannot be whitespace-only")
        return stripped


class FilterBlock(BaseModel):
    data_types: list[DataType] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class ResultItem(BaseModel):
    chunk_id: str
    source_id: str
    source_path: str
    score: float
    data_type: str
    category: str
    text: str
    original_metadata: dict[str, str] = Field(default_factory=dict)


class StatsBlock(BaseModel):
    total_candidates: int
    returned: int
    elapsed_ms: int


class RerankDetailItem(BaseModel):
    chunk_id: str
    pre_rank_score: float
    post_rank_score: float
    rerank_explanation: str


class DebugBlock(BaseModel):
    recall_candidates: list[ResultItem] = Field(default_factory=list)
    rerank_detail: list[RerankDetailItem] = Field(default_factory=list)


class RetrieveResponse(BaseModel):
    api_version: Literal["1"] = "1"
    query: str
    k: int
    results: list[ResultItem] = Field(default_factory=list)
    stats: StatsBlock
    debug: DebugBlock | None = None


class HealthResponse(BaseModel):
    api_version: Literal["1"] = "1"
    status: str
    index_loaded: bool
    embedding_model: str
    detail: str | None = None


class IndexStatsResponse(BaseModel):
    api_version: Literal["1"] = "1"
    chunk_count: int
    source_count: int
    by_data_type: dict[str, int]
    embedding_model: str
    embedding_dim: int
    last_ingest_at: str | None
    index_path: str


class ErrorResponse(BaseModel):
    api_version: Literal["1"] = "1"
    error: str
    detail: str | list[dict] = ""
