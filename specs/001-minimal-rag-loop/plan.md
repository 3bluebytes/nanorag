# Implementation Plan: RAG Nano v1 — Minimal Closed Loop (Librarian Layer)

**Branch**: `001-minimal-rag-loop` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification at `specs/001-minimal-rag-loop/spec.md`

## Summary

Deliver the librarian layer of the broader RAG-driven assistant system — a single, agent‑neutral knowledge service that an external orchestrator can dispatch "work orders" (queries) to and receive ranked, fully‑attributed results from. v1 is the minimum closed loop required by Constitution principle II: ingest, retrieval, evaluation. Nothing else.

Technical approach (per research.md, Constitution V/VI):

- **Python 3.11+** as the implementation language; `uv` for dep management; `pyproject.toml` (PEP 621) as the manifest.
- **FastAPI + uvicorn** for the local HTTP server (single deliverable per Q1 in spec).
- **`sentence-transformers` + `intfloat/multilingual-e5-base`** as the v1 reference embedding (mixed Chinese + English, fits comfortably on a workstation; BGE-m3 is the documented upgrade path).
- **NumPy flat vector store** (in-memory + on-disk persistence) as the v1 reference; sized for the ≤50k chunk target. Exact-search at this scale is faster than FAISS setup overhead and zero added deps.
- **SQLite** as the structured store (built-in, queryable, zero deps).
- **Typer** for the CLI (`ingest`, `serve`, `eval`, `wipe-index`, `stats`).
- **Pydantic Settings** for config; **stdlib logging** for now.
- **pytest + pytest-asyncio** for tests.
- All six core components (embedding, vector store, retriever, metadata extractor, reranker, structured store) defined as `typing.Protocol` contracts in `components/protocols.py`, with a `factory.py`-style helper that selects an implementation from configuration. Each component ships ≥1 reference + ≥1 mock implementation in v1 (Constitution V satisfied).
- Reranker v1 body is the identity function; the interface is exercised by retrieval and tests so a real reranker is a drop-in addition (Constitution IX).

## Technical Context

**Language/Version**: Python 3.11+ (typing.Protocol mature, asyncio stable, pattern matching available)
**Primary Dependencies**: FastAPI, uvicorn, pydantic, pydantic-settings, sentence-transformers (PyTorch-backed), numpy, typer, pyyaml
**Storage**: SQLite (structured metadata + chunks); NumPy `.npy` files on disk (vector index persistence); local filesystem for raw eval set + history JSONL
**Testing**: pytest + pytest-asyncio (HTTP), pytest-mock (component substitution), `httpx.AsyncClient` for in-process HTTP testing
**Target Platform**: Local developer workstation (macOS / Linux / WSL); no production hosting requirement in v1
**Project Type**: Python service with HTTP API + CLI (single project, src-layout)
**Performance Goals**: <2s p95 per `/v1/retrieve` call on the reference local setup at 50k chunks (per spec Assumption); ingest throughput target deferred to v2
**Constraints**: Offline-capable after first model download; single-tenant; no external network at query time; ≤50k chunks; ≤5k source documents
**Scale/Scope**: ≤50k chunks; 6 swappable components; 22 functional requirements; 7 success criteria; ≥20 evaluation cases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | How v1 satisfies |
|---|-----------|--------|------------------|
| I | Documentation Before Implementation | ✅ Pass | spec.md → clarify session → plan.md → research.md → data-model.md → contracts/ → quickstart.md, all ratified before any code is written. |
| II | Minimal Closed Loop First | ✅ Pass | v1 = ingest + retrieval + evaluation only. No multi-agent, no UI beyond CLI, no MQ/graph DB/permissions. FR-022 enumerates the prohibition list. |
| III | High-Value Knowledge Priority | ✅ Pass | FR-008 restricts ingest to the 10 high-value data types named in Constitution III. Value-gate component enforces at the boundary. |
| IV | Cold Data Prohibition | ✅ Pass | FR-009 (extended) rejects cold data and high-confidence credential matches at the ingest gate with per-item reason. PII scrubbing remains an external pre-processing concern (documented in Assumptions). |
| V | Swappable Core Components | ✅ Pass | All 6 components defined as Protocols + factory; each ships 1 reference + 1 mock impl in v1. `tests/integration/test_swappability.py` proves substitution works. Business code never imports concrete impls. |
| VI | Pragmatic Technology Selection | ✅ Pass | research.md records ≥2 candidates per choice with selection rationale. All choices favor local debuggability over novelty. |
| VII | Explainable Retrieval | ✅ Pass | FR-004/005/006 enforce source + score + data type + category + metadata on every hit; debug mode exposes recall + rerank intermediate state. The HTTP contract has no path that returns an unattributed result. |
| VIII | Loose Coupling with Agents | ✅ Pass | FR-001 forbids agent-specific logic in the contract. quickstart.md ships two integration examples (chat-agent style and workflow-agent style) using only the public HTTP API. |
| IX | Subtraction Over Addition | ✅ Pass | Reranker body is identity in v1; HostedAPIEmbeddingProvider, alternative vector stores, AST-aware code chunkers are all interface-only or absent. Each deferral is documented in research.md with trigger conditions for promotion. |
| X | Minimum Evaluation Required | ✅ Pass | FR-018-021 + Assumption block require ≥20 cases spanning all v1 data types in both Chinese and English; eval CLI persists results to `eval/history.jsonl` for trend tracking. |

**Initial gate**: PASS (all 10). Re-evaluated after Phase 1 design — still PASS (no new dependencies introduced beyond research.md).

## Project Structure

### Documentation (this feature)

```text
specs/001-minimal-rag-loop/
├── plan.md                  # this file
├── spec.md                  # what & why
├── research.md              # technology selection (Constitution VI)
├── data-model.md            # entities + persistence schema
├── contracts/
│   └── retrieval-api.md     # HTTP API contract (FR-001..007)
├── quickstart.md            # local setup + 2 integration examples (Constitution VIII)
├── checklists/
│   └── requirements.md      # spec quality checklist (closed)
└── tasks.md                 # /speckit.tasks output (next phase)
```

### Source Code (repository root)

```text
rag_nano/                          # main package (src-layout under pyproject)
├── __init__.py
├── api/                            # HTTP layer (FastAPI)
│   ├── __init__.py
│   ├── app.py                      # FastAPI app factory
│   ├── models.py                   # Pydantic request/response
│   └── routes.py                   # endpoint handlers (/v1/retrieve, /v1/health, /v1/index/stats)
├── core/                           # service-level orchestration
│   ├── __init__.py
│   ├── retrieval.py                # query → embed → search → rerank → format
│   └── ingest.py                   # batch → load → value-gate → credential-scan → chunk → embed → persist
├── components/                     # swappable Protocols + impls (Constitution V)
│   ├── __init__.py
│   ├── protocols.py                # all 6 Protocols (canonical contracts)
│   ├── embedding.py                # LocalSTProvider + MockEmbeddingProvider + factory
│   ├── vector_store.py             # NumpyFlatVectorStore + InMemoryVectorStore + factory
│   ├── retriever.py                # CosineTopKRetriever + MockRetriever + factory
│   ├── reranker.py                 # IdentityReranker + MockReranker + factory
│   ├── metadata_extractor.py       # DefaultMetadataExtractor + MockMetadataExtractor + factory
│   └── structured_store.py         # SqliteStructuredStore + InMemoryStructuredStore + factory
├── ingest/                         # ingest pipeline
│   ├── __init__.py
│   ├── loaders.py                  # file → RawItem (markdown/text/code dispatch)
│   ├── value_gate.py               # data-type classification + cold-data rejection (FR-008/009a)
│   ├── credential_scan.py          # regex-based credential rejection (FR-009b)
│   ├── chunker.py                  # RawItem → list[Chunk] (markdown-aware + code-line-based)
│   └── runner.py                   # orchestrates value_gate → credential_scan → chunker → embed → persist
├── eval/                           # evaluation harness
│   ├── __init__.py
│   ├── runner.py                   # load cases → run retrievals → compute metrics → persist run
│   ├── metrics.py                  # recall@k, hit_rate
│   └── history.py                  # append + diff against previous run
├── cli/                            # Typer commands
│   ├── __init__.py
│   └── main.py                     # ingest, serve, eval, wipe-index, stats
├── config.py                       # Pydantic Settings (env + .env)
├── logging_setup.py                # stdlib logging configuration
└── types.py                        # cross-cutting types: DataType enum, KnowledgeChunk, RetrievalResult, etc.

tests/
├── conftest.py                     # fixtures: tmp index dir, mock components, seed corpus
├── contract/                       # tests against HTTP contract (FR-001..007)
│   └── test_retrieval_api.py
├── integration/
│   ├── test_ingest_pipeline.py     # acceptance scenarios for User Story 2
│   ├── test_retrieval_e2e.py       # acceptance scenarios for User Story 1
│   ├── test_eval_pipeline.py       # acceptance scenarios for User Story 3
│   ├── test_swappability.py        # Constitution V proof: every component swaps cleanly
│   └── test_concurrent_access.py   # ingest/retrieval concurrency (Assumption: atomic per source)
├── unit/
│   ├── test_embedding.py
│   ├── test_vector_store.py
│   ├── test_retriever.py
│   ├── test_reranker.py
│   ├── test_metadata_extractor.py
│   ├── test_structured_store.py
│   ├── test_chunker.py
│   ├── test_value_gate.py
│   ├── test_credential_scan.py
│   └── test_metrics.py
└── fixtures/                       # small docs, code samples, mock cases

eval/
├── cases.yaml                      # ≥20 query→expected pairs (≥1 case per data type, both Chinese & English)
├── history.jsonl                   # appended one JSON per run; never rewritten
└── README.md                       # how to add a case

scripts/
├── download_models.sh              # one-shot: pre-fetch embedding model weights
└── seed_dev_corpus.sh              # populate index with sample corpus for local play

pyproject.toml                      # PEP 621 manifest; `uv` resolves the lock file
README.md                           # short — points at quickstart.md
.env.example                        # config template (model id, paths, log level)
```

**Structure Decision**: Single Python project, src-layout-flavor with the package at the repo root (`rag_nano/`) for simplicity. Six swappable components live in `rag_nano/components/`, one file per component holding (a) the Protocol import from `protocols.py`, (b) the v1 reference impl, (c) the mock impl, and (d) a `get_<component>()` factory function. Service-level orchestration sits in `rag_nano/core/`; pipeline-specific logic in `rag_nano/ingest/` and `rag_nano/eval/`; HTTP surface in `rag_nano/api/`; CLI surface in `rag_nano/cli/`. Tests mirror this structure with separate `contract/` (HTTP), `integration/` (cross-component flows including `test_swappability.py` as the Constitution V gate test), and `unit/` directories.

## Complexity Tracking

> Constitution Check passed all 10 principles. No violations to justify.

(Section intentionally empty.)
