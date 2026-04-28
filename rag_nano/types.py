from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DataType(str, Enum):
    document = "document"
    faq = "faq"
    sop = "sop"
    case_study = "case_study"
    issue_summary = "issue_summary"
    wiki = "wiki"
    config_note = "config_note"
    knowledge_card = "knowledge_card"
    code_summary = "code_summary"
    log_summary = "log_summary"


class RejectionReason(str, Enum):
    cold_data_raw_log = "cold_data_raw_log"
    cold_data_raw_dump = "cold_data_raw_dump"
    cold_data_raw_trace = "cold_data_raw_trace"
    cold_data_oversized_conversation = "cold_data_oversized_conversation"
    cold_data_duplicate = "cold_data_duplicate"
    unsupported_format = "unsupported_format"
    credential_aws_access_key = "credential_aws_access_key"
    credential_github_pat = "credential_github_pat"
    credential_stripe_key = "credential_stripe_key"
    credential_jwt = "credential_jwt"
    credential_generic_assignment = "credential_generic_assignment"
    embedding_failure = "embedding_failure"


@dataclass
class KnowledgeSource:
    source_id: str
    source_path: str
    data_type: DataType
    category: str
    content_hash: str
    ingested_at: datetime
    chunk_count: int
    original_metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class KnowledgeChunk:
    chunk_id: str
    source_id: str
    text: str
    position: int
    embedding_index: int
    data_type: DataType
    category: str
    original_metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class RetrievalQuery:
    query: str
    k: int = 5
    filters: RetrievalFilters = field(default_factory=lambda: RetrievalFilters())
    debug: bool = False


@dataclass
class RetrievalFilters:
    data_types: list[DataType] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class RetrievalResultRecord:
    chunk_id: str
    source_id: str
    source_path: str
    score: float
    data_type: DataType
    category: str
    text: str
    original_metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class RetrievalDebugDetail:
    recall_candidates: list[RetrievalResultRecord] = field(default_factory=list)
    rerank_detail: list[RerankDetailEntry] = field(default_factory=list)


@dataclass
class RerankDetailEntry:
    chunk_id: str
    pre_rank_score: float
    post_rank_score: float
    rerank_explanation: str


@dataclass
class RetrievalResponse:
    query: str
    k: int
    results: list[RetrievalResultRecord] = field(default_factory=list)
    stats: RetrievalStats = field(default_factory=lambda: RetrievalStats())
    debug: RetrievalDebugDetail | None = None


@dataclass
class RetrievalStats:
    total_candidates: int = 0
    returned: int = 0
    elapsed_ms: int = 0


@dataclass
class EvaluationCase:
    case_id: str
    query: str
    query_lang: str
    expected_data_type: DataType
    mode: str
    expected_chunk_ids: list[str] = field(default_factory=list)
    expected_substring: str = ""
    notes: str = ""


@dataclass
class EvaluationRun:
    run_id: str
    started_at: datetime
    finished_at: datetime
    case_count: int
    metric_recall_at_k: float
    metric_hit_rate: float
    k: int
    embedding_model: str
    index_chunk_count: int
    per_case_outcome: list[dict] = field(default_factory=list)
    delta_vs_previous: dict | None = None
    git_sha: str | None = None


@dataclass
class IngestRunReport:
    accepted: int = 0
    rejected: int = 0
    total_chunks: int = 0
    per_item_reasons: list[tuple[str, RejectionReason | None]] = field(default_factory=list)
    by_data_type: dict[str, int] = field(default_factory=dict)
