# Contract: Retrieval HTTP API

**Feature**: 001-minimal-rag-loop · **Date**: 2026-04-28
**Status**: v1 contract — once frozen, breaking changes increment `api_version` and live alongside until consumers migrate.

This document is the agent-neutral, stable contract that satisfies FR-001/002/003/004/005/006/007. The librarian publishes only this surface; nothing about specific agents (prompts, dialogue formats, business logic) appears here or in the implementation behind it (Constitution VIII).

The implementation in `rag_nano/api/` MUST conform to this document. Discrepancies are bugs in the code, not in this contract.

---

## Endpoint inventory

| Method | Path | Purpose | Spec FR refs |
|--------|------|---------|--------------|
| `POST` | `/v1/retrieve` | Submit a query; receive ranked, attributed results. | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007 |
| `GET`  | `/v1/health` | Liveness + index readiness probe. | (operational) |
| `GET`  | `/v1/index/stats` | Inspect current index size + last-ingest metadata. | (operational) |

**Out of scope for v1 HTTP**: ingest, wipe, and eval are CLI-only commands. Ingest as an HTTP endpoint is documented in research.md as a v2 trigger.

All endpoints return `Content-Type: application/json; charset=utf-8`. All responses include the `api_version` field.

---

## `POST /v1/retrieve`

### Request

```http
POST /v1/retrieve HTTP/1.1
Content-Type: application/json
```

```json
{
  "query": "如何配置 BGE-m3 的 prefix?",
  "k": 5,
  "filters": {
    "data_types": ["faq", "sop"],
    "categories": ["embedding", "ops"]
  },
  "debug": false
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|:--------:|---------|-------------|
| `query` | string | ✓ | — | 1 ≤ length ≤ 2000 chars. Trimmed; whitespace-only → 422. |
| `k` | int | — | 5 | 1 ≤ k ≤ 50. |
| `filters.data_types` | string[] | — | `[]` | Each value MUST be a member of `DataType` (see data-model.md). Empty list = no filter. Multi-value semantics: any-match. |
| `filters.categories` | string[] | — | `[]` | Free-form strings. Multi-value semantics: any-match. |
| `debug` | bool | — | `false` | When `true`, response includes `debug` block. |

### Success response (200)

```json
{
  "api_version": "1",
  "query": "如何配置 BGE-m3 的 prefix?",
  "k": 5,
  "results": [
    {
      "chunk_id": "01HV5R3MAW5K9VAB6H8B6K7Q5N",
      "source_id": "01HV5R3M2YV6FQ4MBG3VFV1XJC",
      "source_path": "knowledge/faq/embedding-faq.md",
      "score": 0.8421,
      "data_type": "faq",
      "category": "embedding",
      "text": "BGE-m3 query prefix should be ...",
      "original_metadata": {
        "author": "ops-team",
        "updated_at": "2026-03-12"
      }
    }
  ],
  "stats": {
    "total_candidates": 142,
    "returned": 1,
    "elapsed_ms": 87
  }
}
```

| Top-level field | Type | Notes |
|-----------------|------|-------|
| `api_version` | string | Always `"1"` for v1. |
| `query` | string | Echo of the input query. |
| `k` | int | Echo of the effective `k` (after default fill). |
| `results` | array | Ordered by relevance descending. May be empty (no error). |
| `stats.total_candidates` | int | Number of chunks the retriever considered before top-k. |
| `stats.returned` | int | `len(results)`. |
| `stats.elapsed_ms` | int | Wall-clock retrieval latency. |
| `debug` | object | Present iff request `debug: true`. See below. |

Each `results[]` item MUST carry **all** of: `chunk_id`, `source_id`, `source_path`, `score`, `data_type`, `category`, `text`, `original_metadata`. **No partial results** — a chunk lacking provenance is dropped at response-build time (FR-005), not returned with null fields.

**`results: []` is a valid 200 response**, not an error (FR-007).

### Debug response (200, `debug: true`)

```json
{
  "api_version": "1",
  "query": "...",
  "k": 5,
  "results": [...],
  "stats": {...},
  "debug": {
    "recall_candidates": [
      {
        "chunk_id": "01HV...",
        "source_id": "01HV...",
        "source_path": "...",
        "score": 0.81,
        "data_type": "faq",
        "category": "embedding",
        "text": "...",
        "original_metadata": {}
      }
    ],
    "rerank_detail": [
      {
        "chunk_id": "01HV...",
        "pre_rank_score": 0.81,
        "post_rank_score": 0.81,
        "rerank_explanation": "identity"
      }
    ]
  }
}
```

`debug.recall_candidates` is the pre-rerank top-N where N ≥ k (configured server-side, default `4 * k`). `debug.rerank_detail` is per-candidate rerank tracing in the order the reranker produced.

### Error responses

| Status | Reason | Body |
|--------|--------|------|
| 422 | Empty/whitespace `query`, out-of-range `k`, unknown `DataType` value, malformed JSON | `{ "api_version": "1", "error": "validation_error", "detail": [{...}] }` (FastAPI's standard validation envelope, wrapped with `api_version`) |
| 503 | Embedding provider unavailable, vector store not loaded, etc. | `{ "api_version": "1", "error": "service_unavailable", "detail": "embedding provider failed: <message>" }` |
| 500 | Unexpected internal failure | `{ "api_version": "1", "error": "internal_error", "detail": "<safe message>" }` |

`results: []` for a well-formed query that simply matches nothing is **not** an error — return 200 with an empty array.

---

## `GET /v1/health`

```http
GET /v1/health HTTP/1.1
```

Response 200 when the service is up and the index is loaded; 503 when the index has not been built yet (no chunks).

```json
{
  "api_version": "1",
  "status": "ok",
  "index_loaded": true,
  "embedding_model": "intfloat/multilingual-e5-base"
}
```

```json
{
  "api_version": "1",
  "status": "degraded",
  "index_loaded": false,
  "embedding_model": "intfloat/multilingual-e5-base",
  "detail": "no chunks ingested yet"
}
```

`/v1/health` MUST not require a model load — it answers from cached state.

---

## `GET /v1/index/stats`

```http
GET /v1/index/stats HTTP/1.1
```

```json
{
  "api_version": "1",
  "chunk_count": 12453,
  "source_count": 387,
  "by_data_type": {
    "faq": 1240,
    "sop": 980,
    "wiki": 5012,
    "code_summary": 3200,
    "knowledge_card": 2021
  },
  "embedding_model": "intfloat/multilingual-e5-base",
  "embedding_dim": 768,
  "last_ingest_at": "2026-04-27T03:14:22Z",
  "index_path": "/Users/.../rag-nano-index"
}
```

Returns 200 even when the index is empty (counts will be zero); never 503 from this endpoint.

---

## Versioning

- The literal value `"api_version": "1"` is part of v1's stable contract.
- Backwards-compatible additions (new optional request fields, new optional response fields, new endpoints) DO NOT increment.
- Breaking changes (removed fields, changed types, changed semantics) MUST increment to `"2"` AND live in parallel under `/v2/...` paths during any migration window.

## What this contract deliberately does NOT include

- No agent-specific prompt templates or output formats. The librarian returns chunks; agents construct prompts.
- No dialogue / session state. Each `/v1/retrieve` call is independent.
- No streaming or async response modes (Assumption: synchronous in v1).
- No authentication / authorization. Single-tenant local v1.
- No quota / rate limiting.
- No ingest, wipe, or admin operations over HTTP.

These are documented exclusions, not oversights — they live behind the same Protocol-shaped extension points so a v2 can add them without touching the contract above.
