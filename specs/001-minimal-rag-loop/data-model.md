# Phase 1 Data Model

**Feature**: 001-minimal-rag-loop · **Date**: 2026-04-28

This document defines the entities the v1 librarian operates on, their fields and validation rules, the relationships between them, and the persistence schema. All entities map directly to Pydantic models in `rag_nano/types.py` (in-memory) and SQLite tables in `rag_nano/components/structured_store.py` (persisted).

---

## Enumerations

### `DataType`

The closed set of high-value data types accepted by the ingest gate (FR-008).

| Value | Description |
|-------|-------------|
| `document` | General prose document |
| `faq` | FAQ entry |
| `sop` | Standard Operating Procedure |
| `case_study` | Historical case write-up / post-mortem summary |
| `issue_summary` | Summary of an issue or bug report |
| `wiki` | Wiki page |
| `config_note` | Configuration / settings note |
| `knowledge_card` | Structured knowledge card |
| `code_summary` | Summary or curated extract of source code |
| `log_summary` | Summary of logs (NOT raw logs — those are cold data) |

### `RejectionReason`

The closed set of reasons an ingest item can be rejected at the gate (FR-009).

| Value | Description |
|-------|-------------|
| `cold_data_raw_log` | Looks like a raw log file |
| `cold_data_raw_dump` | Full source dump or raw export |
| `cold_data_raw_trace` | Raw execution trace |
| `cold_data_oversized_conversation` | Raw conversation transcript over size threshold |
| `cold_data_duplicate` | Duplicate of an already-ingested source |
| `unsupported_format` | File extension not in the v1 supported list |
| `credential_aws_access_key` | Matched AWS access key pattern |
| `credential_github_pat` | Matched GitHub personal access token pattern |
| `credential_stripe_key` | Matched Stripe key pattern |
| `credential_jwt` | Matched JWT pattern |
| `credential_generic_assignment` | Matched generic `password=` / `api_key=` / `secret=` pattern |
| `embedding_failure` | Embedding inference failed for this item; ingest aborted atomically per source |

---

## Entities

### `KnowledgeSource`

The origin of a piece of ingested content.

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `source_id` | str (ULID) | ✓ | Stable, monotonic, sortable. One per logical ingest source. |
| `source_path` | str | ✓ | Filesystem path (or URI) the operator passed to ingest. |
| `data_type` | DataType | ✓ | Classified by the value gate. |
| `category` | str | ✓ | Free-form category label (from frontmatter, parent dir, or operator-supplied). |
| `content_hash` | str (sha256 hex) | ✓ | SHA-256 of the raw input bytes. Used for the dedup check in FR-012. |
| `ingested_at` | datetime (UTC, ISO 8601) | ✓ | Timestamp of successful commit. |
| `chunk_count` | int | ✓ | Number of chunks produced from this source. |
| `original_metadata` | dict[str, str] | ✓ | Caller-or-frontmatter-supplied metadata; never mutated after ingest. |

**Identity & uniqueness**: `source_id` is the primary key. `(source_path, content_hash)` is also unique — re-ingesting the same path with identical content is a no-op (FR-012); re-ingesting the same path with new content replaces the previous source's chunks atomically.

**Lifecycle**: created exactly once per successful ingest commit. Deleted only by `wipe-index` (no per-source delete in v1). Re-ingest of the same path is delete-then-recreate within a single transaction (matches the FR-012 "replace" semantics).

### `KnowledgeChunk`

A retrievable unit produced from a `KnowledgeSource`.

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `chunk_id` | str (ULID) | ✓ | Stable per chunk. |
| `source_id` | str (ULID) | ✓ | FK to `KnowledgeSource.source_id`. |
| `text` | str | ✓ | The chunk's payload. ≤ 8 KiB. |
| `position` | int | ✓ | 0-based ordinal within the parent source. |
| `embedding_index` | int | ✓ | Row offset into the vector store's NumPy matrix. |
| `data_type` | DataType | ✓ | Inherited from parent source (denormalized for filter speed). |
| `category` | str | ✓ | Inherited from parent source (denormalized). |
| `original_metadata` | dict[str, str] | ✓ | Inherited from parent source. |

**Identity & uniqueness**: `chunk_id` is the primary key. `(source_id, position)` is also unique. `embedding_index` is unique within the active vector store snapshot.

**Lifecycle**: created with parent source. Garbage-collected with parent source on re-ingest replace or `wipe-index`.

### `RetrievalQuery`

The inbound query as it arrives at `POST /v1/retrieve`. Validated by Pydantic.

| Field | Type | Required | Default | Notes |
|-------|------|:--------:|---------|-------|
| `query` | str | ✓ | — | 1 ≤ len ≤ 2000 chars. Whitespace-only rejected with 422. |
| `k` | int | — | 5 | 1 ≤ k ≤ 50. |
| `filters` | object | — | `{}` | See sub-fields. |
| `filters.data_types` | list[DataType] | — | `[]` (= all) | At-least-one-match semantics. |
| `filters.categories` | list[str] | — | `[]` (= all) | At-least-one-match semantics. |
| `debug` | bool | — | `false` | When `true`, response includes `recall_candidates` and `rerank_detail`. |

**Validation rules**: Pydantic enforces field types, length bounds, and the `DataType` enum. Empty/whitespace queries are rejected before any retrieval cost is incurred (edge case in spec).

### `RetrievalResult`

A single hit returned to the caller (FR-004).

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `chunk_id` | str | ✓ | |
| `source_id` | str | ✓ | |
| `source_path` | str | ✓ | Surface-level provenance for the caller. |
| `score` | float | ✓ | Cosine similarity in [0, 1]. |
| `data_type` | DataType | ✓ | |
| `category` | str | ✓ | |
| `text` | str | ✓ | The chunk text. |
| `original_metadata` | dict[str, str] | ✓ | As-ingested. |

**Invariant** (enforced by FR-005): every `RetrievalResult` returned to the caller has a non-empty `source_id` AND `source_path`. Any chunk in the index that fails this check is skipped at response-build time and logged.

### `RetrievalDebugDetail` (optional, only when `debug=true`)

| Field | Type | Notes |
|-------|------|-------|
| `recall_candidates` | list[RetrievalResult] | Pre-rerank top-N (where N ≥ k). |
| `rerank_detail` | list[object] | One entry per candidate: `{chunk_id, pre_rank_score, post_rank_score, rerank_explanation}` |

The identity reranker fills `post_rank_score = pre_rank_score` and `rerank_explanation = "identity"`; future rerankers populate meaningfully.

### `EvaluationCase`

One entry in `eval/cases.yaml`.

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `case_id` | str | ✓ | Human-readable, stable across runs (e.g. `faq-zh-001`). |
| `query` | str | ✓ | The query to issue. |
| `query_lang` | "zh" \| "en" \| "mixed" | ✓ | Required for the eval composition rule. |
| `expected_data_type` | DataType | ✓ | The data type the case validates against. |
| `expected_chunk_ids` | list[str] | ✓ when `mode = "chunk_ids"` | One or more `chunk_id`s the result should include. |
| `expected_substring` | str | ✓ when `mode = "substring"` | A substring expected to appear in at least one returned chunk's `text`. |
| `mode` | "chunk_ids" \| "substring" | ✓ | Determines which of the above two fields applies. |
| `notes` | str | — | Free-form context for the case author. |

**Composition rule** (Assumption + FR-018):
- ≥ 20 cases total in v1
- ≥ 1 case per `expected_data_type` that appears in the corpus
- ≥ 1 `query_lang = "zh"` case AND ≥ 1 `query_lang = "en"` case overall

The eval runner enforces these structural rules at startup; missing them is a hard error (not a per-case warning).

### `EvaluationRun`

One execution of `rag-nano eval`. Persisted as a single JSON line in `eval/history.jsonl`.

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `run_id` | str (ULID) | ✓ | |
| `started_at` | datetime (UTC) | ✓ | |
| `finished_at` | datetime (UTC) | ✓ | |
| `case_count` | int | ✓ | |
| `metric_recall_at_k` | float | ✓ | k from the run config. |
| `metric_hit_rate` | float | ✓ | Free secondary metric. |
| `k` | int | ✓ | Default 5. |
| `embedding_model` | str | ✓ | E.g. `intfloat/multilingual-e5-base`. Captured for reproducibility. |
| `index_chunk_count` | int | ✓ | Snapshot of the index size at run time. |
| `git_sha` | str (40-char hex) \| null | — | If invoked inside a git tree. |
| `per_case_outcome` | list[object] | ✓ | `{case_id, hit, expected_rank, top_k_returned}` |
| `delta_vs_previous` | object \| null | — | `{previous_run_id, recall_delta, hit_rate_delta}`; null on first run. |

**Lifecycle**: append-only. Never edited or removed in code paths. Operator can manually edit / truncate `eval/history.jsonl` outside of code.

---

## Relationships

```
KnowledgeSource (1) ───< (N) KnowledgeChunk
                                  │
                                  └──< 1 row in vector store @ embedding_index

RetrievalQuery ──> RetrievalResult[]   (many)
                          │
                          └──> traces back to KnowledgeChunk via chunk_id
                                       └──> traces back to KnowledgeSource via source_id

EvaluationCase (1..N) ──> EvaluationRun (one run executes all cases)
                                  │
                                  └──< 1 record in eval/history.jsonl
```

## Persistence layout (SQLite + filesystem)

### SQLite tables (`<index_dir>/structured.db`)

```sql
CREATE TABLE knowledge_source (
  source_id        TEXT PRIMARY KEY,         -- ULID
  source_path      TEXT NOT NULL,
  data_type        TEXT NOT NULL,
  category         TEXT NOT NULL,
  content_hash     TEXT NOT NULL,
  ingested_at      TEXT NOT NULL,            -- ISO 8601 UTC
  chunk_count      INTEGER NOT NULL,
  original_metadata_json TEXT NOT NULL,
  UNIQUE (source_path, content_hash)
);

CREATE TABLE knowledge_chunk (
  chunk_id         TEXT PRIMARY KEY,         -- ULID
  source_id        TEXT NOT NULL REFERENCES knowledge_source(source_id) ON DELETE CASCADE,
  text             TEXT NOT NULL,
  position         INTEGER NOT NULL,
  embedding_index  INTEGER NOT NULL UNIQUE,
  data_type        TEXT NOT NULL,            -- denormalized
  category         TEXT NOT NULL,            -- denormalized
  original_metadata_json TEXT NOT NULL,      -- denormalized
  UNIQUE (source_id, position)
);

CREATE INDEX idx_chunk_data_type ON knowledge_chunk(data_type);
CREATE INDEX idx_chunk_category  ON knowledge_chunk(category);
```

WAL mode enabled at connection time (`PRAGMA journal_mode=WAL`) so retrieval reads do not block ingest writes.

### Vector store layout (`<index_dir>/vectors/`)

```
<index_dir>/vectors/
├── matrix.npy             # float32, shape = (chunk_count, embedding_dim)
├── id_map.json            # list[str]; row i → chunk_id
└── manifest.json          # {embedding_model, dim, created_at, chunk_count, sha256}
```

**Atomic swap protocol**: ingest builds a complete new `matrix.npy` + `id_map.json` + `manifest.json` set in `<index_dir>/vectors_next/`, then renames the directory to `vectors/` (POSIX `rename` is atomic on the same filesystem). Live retrieval keeps a file handle / mmap on the old `matrix.npy` until its current request completes; next request opens the new one. SQLite changes commit in the same transaction window so the structured store and the vector matrix are mutually consistent at every observable moment.

### Eval layout (`eval/`)

```
eval/
├── cases.yaml             # source of truth for cases
├── history.jsonl          # append-only run records
└── README.md
```

---

## Cross-references to Functional Requirements

| Requirement | Where it lives in the model |
|-------------|------------------------------|
| FR-002 (filters: data type, category) | `RetrievalQuery.filters.{data_types,categories}`; SQL indexes on `knowledge_chunk` |
| FR-004 (every result attributed) | `RetrievalResult` mandatory fields |
| FR-005 (no untraceable result) | Enforced at response build; chunks lacking `source_id` skipped + logged |
| FR-006 (debug mode) | `RetrievalQuery.debug` → `RetrievalDebugDetail` in response |
| FR-008 (data type whitelist) | `DataType` enum |
| FR-009 (cold-data + credential rejection) | `RejectionReason` enum + per-item entries in ingest run report |
| FR-011 (chunk traceability) | `KnowledgeChunk.source_id` FK constraint |
| FR-012 (no duplicate sources) | `(source_path, content_hash)` UNIQUE; replace-on-content-change semantics |
| FR-014 (atomic ingest per source) | SQLite transaction wrapping the per-source insert + atomic vector-dir rename |
| FR-018 (≥20 cases) | Eval runner startup check |
| FR-020 (history + delta) | `eval/history.jsonl` + `delta_vs_previous` field |
