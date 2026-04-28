# Phase 0 Research: Technology Selection

**Feature**: 001-minimal-rag-loop · **Date**: 2026-04-28

This document records each non-trivial technology choice for v1 along with the rejected alternative(s) and the rationale. Constitution VI requires every choice to surface ≥2 candidates and explain the pick; that gate is enforced here.

---

## R1. Implementation language

- **Decision**: Python 3.11+
- **Alternatives considered**:
  - Node/TypeScript: weaker ML ecosystem, no first-class `sentence-transformers` equivalent, adds friction for the embedding/vector path.
  - Rust: high engineering cost for v1 minimum loop; embedding inference is still PyTorch-bound.
- **Rationale**: The entire local-embedding + vector-store ecosystem in 2026 is Python-first. `typing.Protocol` makes the swappable contract pattern (Constitution V) trivial to express. Pattern matching and structural typing (3.10+) cleanly express the multi-data-type ingest dispatch.
- **Trigger to revisit**: a non-Python runtime requirement for the embedding host (e.g. running on a constrained edge device).

## R2. Dependency / project manager

- **Decision**: `uv` + `pyproject.toml` (PEP 621)
- **Alternatives considered**:
  - `pip` + `requirements.txt` + `requirements-dev.txt`: simplest, no lock file, slow resolution.
  - Poetry: heavier, slower install path, opinionated about virtual envs.
  - Pipenv: in maintenance mode, not recommended for new projects.
- **Rationale**: `uv` (Astral) installs ~10-100× faster than pip, produces a deterministic lock file, supports PEP 621, and reads/writes the same `pyproject.toml` other tools understand. Pure additive — anyone with vanilla `pip` can still install.
- **Trigger to revisit**: organizational mandate to use a different tool.

## R3. HTTP framework

- **Decision**: FastAPI + uvicorn
- **Alternatives considered**:
  - Starlette directly (FastAPI is built on it): lower level, lose automatic Pydantic-driven validation and OpenAPI generation.
  - Flask + Flask-RESTX: synchronous-first; adds adapters for async embedding inference; less idiomatic in 2026.
  - aiohttp: lower-level async server, no built-in schema validation.
- **Rationale**: FastAPI gives Pydantic-validated request/response, automatic OpenAPI generation (we get a machine-readable contract for free), and a typed async-friendly handler signature. uvicorn is the canonical ASGI server. Both ship in the FastAPI ecosystem with one install.
- **Trigger to revisit**: needing a framework with built-in background workers / queues — but those are explicitly out of v1 scope.

## R4. Embedding inference library

- **Decision**: `sentence-transformers` (PyTorch backend)
- **Alternatives considered**:
  - `transformers` (HuggingFace) directly: lower level, requires hand-rolling pooling + L2 normalization.
  - `fastembed` (Qdrant): ONNX-based, faster CPU inference, smaller dep footprint — but smaller model catalog and less battle-tested with multilingual-e5 / BGE-m3.
- **Rationale**: `sentence-transformers` is the documented loader path for both candidate models (multilingual-e5 and BGE-m3). It handles pooling, normalization, batching, and device selection (CPU / MPS / CUDA) with one line. Cost: PyTorch is a heavy dependency (~200MB), accepted trade-off for v1 simplicity.
- **Trigger to revisit**: the PyTorch dep becomes a runtime/distribution problem (e.g. moving to a stripped container) — at which point swap in `fastembed` behind the same `EmbeddingProvider` Protocol with zero consumer changes (Constitution V proof point).

## R5. Concrete embedding model for v1

- **Decision**: `intfloat/multilingual-e5-base` (278M params, 768-dim, mean-pooled, L2-normalized, supports the `"query: "` / `"passage: "` prefix convention)
- **Alternatives considered**:
  - `BAAI/bge-m3` (568M params, 1024-dim, multilingual + multi-functional sparse/dense/colbert): stronger Chinese, larger weights (~2.3GB), heavier inference, and overkill for the v1 corpus target (≤50k chunks).
  - `intfloat/multilingual-e5-large` (560M params, 1024-dim): same family, ~2× the inference cost of base.
  - `BAAI/bge-small-en` (33M, English only): too small + monolingual; excluded by mixed Chinese + English requirement.
- **Rationale**: e5-base is the smallest model that is well-evaluated on both Chinese and English passage retrieval. ~278M params runs comfortably on CPU and Apple Silicon MPS in <100ms per query. 768-dim vectors keep the on-disk index small (50k × 768 × 4 bytes ≈ 150MB).
- **Trigger to revisit**: recall@k on the eval set is below the team's bar after a fair run — the documented promotion path is bge-m3.

## R6. Vector store

- **Decision**: `NumpyFlatVectorStore` — exact cosine similarity over a NumPy float32 matrix, persisted to disk as `.npy` (vectors) + `.json` (id mapping)
- **Alternatives considered**:
  - FAISS (CPU): mature library, but at 50k × 768 the brute-force search is already <50 ms; FAISS adds a ~20MB dep and an index-config decision (`Flat` / `IVF` / `HNSW`) that buys nothing at this scale.
  - Chroma: client+server abstraction, persistent SQLite + DuckDB backend; more deps, more config surface.
  - LanceDB: Arrow-backed columnar storage; modern but adds a non-trivial dep.
  - Qdrant / Weaviate / Milvus (server-mode): completely out of scope for single-workstation v1.
- **Rationale**: At ≤50k chunks the simplest possible thing — a NumPy array on disk + brute-force search — is competitive with any indexed alternative and uses zero additional deps (NumPy is already required by `sentence-transformers`). This is exactly the "pragmatic, locally debuggable" choice Constitution VI calls for.
- **Trigger to revisit**: corpus growth past ~200k chunks, or query latency exceeds the 2s budget. At that point swap in `FaissFlatVectorStore` (or HNSW) behind the same Protocol.

## R7. Structured store (chunk metadata + run history)

- **Decision**: SQLite (`sqlite3` standard library)
- **Alternatives considered**:
  - JSON / JSONL files: queryability is poor; metadata filters (FR-002) would need a custom in-memory index.
  - DuckDB: powerful for analytics queries, additional dep, more than v1 needs.
  - PostgreSQL (local): server process, deployment overhead, way over-spec for single-tenant v1.
- **Rationale**: Stdlib SQLite is zero-dep, file-based, supports concurrent readers + a single writer (matches the Assumption "ingest writes are atomic per source; retrieval is never blocked"), and gives us SQL for metadata filters (data type, category, source) for free.
- **Trigger to revisit**: filter complexity needs SQL features SQLite lacks (window functions over very large data, etc.). Not anticipated in v1.

## R8. CLI framework

- **Decision**: Typer
- **Alternatives considered**:
  - Click: well-established, more verbose, no type-driven param parsing.
  - argparse (stdlib): zero-dep, more boilerplate, weaker UX (no shell completion, no rich help).
- **Rationale**: Typer is built on Click but uses Python type hints to auto-generate the CLI surface — same DX as FastAPI does for HTTP. One small dep, big ergonomics win for the 5 v1 commands.
- **Trigger to revisit**: not anticipated.

## R9. Configuration

- **Decision**: `pydantic-settings`
- **Alternatives considered**:
  - `python-decouple` / `python-dotenv` raw: no type validation.
  - `dynaconf`: heavier, more layers than v1 needs.
  - hand-rolled `os.environ` reads: no validation, easy to drift.
- **Rationale**: pydantic-settings reads from env, `.env`, or a config file with the same Pydantic types we already use for the HTTP API models. Single source of truth for config schema, automatic validation at startup.
- **Trigger to revisit**: needing hierarchical multi-environment config (dev/staging/prod) — out of v1 scope.

## R10. Logging

- **Decision**: stdlib `logging` with a JSON formatter (one tiny module: `rag_nano/logging_setup.py`)
- **Alternatives considered**:
  - `structlog`: better ergonomics for structured logging; one dep; defer to v2.
  - `loguru`: very ergonomic but uses non-standard sinks; harder to integrate with future observability stacks.
- **Rationale**: stdlib `logging` is zero-dep and fully sufficient for the single-process, single-tenant v1. JSON output (one ~10-line formatter) keeps logs grep-friendly and ready for an external collector later.
- **Trigger to revisit**: when we add any real observability backend (Loki, OpenTelemetry, etc.) — at that point structlog becomes worth the dep.

## R11. Test framework

- **Decision**: pytest + pytest-asyncio + httpx
- **Alternatives considered**:
  - stdlib `unittest`: viable but more boilerplate; weaker fixture model.
- **Rationale**: pytest is the universal Python test runner. `pytest-asyncio` for the async HTTP routes. `httpx.AsyncClient` lets us hit the FastAPI app in-process without spinning up uvicorn — fast, deterministic.

## R12. Chunking strategy

- **Decision**:
  - **Markdown / plain text**: heading-aware split (split on ATX headings level 1-3), then recursive char split per leaf section with `chunk_size = 800` chars and `overlap = 100` chars.
  - **Source code**: line-based windowing with `chunk_size = 80` lines, `overlap = 10` lines, plus a "first comment block / docstring captured separately as the chunk preamble" heuristic.
- **Alternatives considered**:
  - LangChain / LlamaIndex chunkers: heavy framework deps for one feature.
  - Tree-sitter AST-aware code splitting: more accurate boundaries (function/class), but adds a non-trivial dep + per-language grammar files.
  - Token-based windowing (tiktoken): more precise budget control; defer until embedding token budget becomes a constraint.
- **Rationale**: Char- and line-based splitting is dependency-free and good enough for v1 corpus scale and the multilingual-e5 model's 512-token input window. Tree-sitter is the documented upgrade path when code recall@k stalls.
- **Trigger to revisit**: code retrieval recall on the eval set is materially worse than markdown retrieval recall.

## R13. Source-code language list for v1 ingest

- **Decision**: `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rs`, `.java`, `.md`, `.txt`
- **Alternatives considered**:
  - Add `.yaml`, `.toml`, `.json` (config files): high credential-leak risk per FR-009; user value is lower (configs are usually small reference docs better summarized externally).
  - Add `.cpp`, `.h`, `.cs`, `.kt`, etc.: every additional extension is a small chunker test surface; defer until requested.
- **Rationale**: This list covers the languages most likely to host high-value code summaries in modern teams (Python, TS/JS, Go, Rust, Java). The list is defined as a config constant — adding a new extension is a one-line edit + a chunker unit test.

## R14. Reranker

- **Decision**: `IdentityReranker` (returns input order unchanged) as the v1 reference impl
- **Alternatives considered**:
  - `bge-reranker-base` (cross-encoder): adds a second model load (~278M params), real recall@k improvement on hard queries but doubles per-query latency.
  - LLM-based listwise reranker: out of scope for v1; cost + latency.
- **Rationale**: Constitution IX. The v1 deliverable is the swappable architecture — the body of the reranker is allowed to be trivial. The interface is exercised in retrieval and tests so swapping in a real cross-encoder later is one new file (`rag_nano/components/reranker.py:CrossEncoderReranker`) + a config flag.
- **Trigger to revisit**: recall@k acceptable but ordering quality (precision@1) is poor on the eval set.

## R15. Metadata extractor

- **Decision**: `DefaultMetadataExtractor` — reads YAML frontmatter when present (markdown), captures filename + parent dir as fallback `category`, captures first comment block / docstring as fallback `summary`
- **Alternatives considered**:
  - LLM-based extractor: high cost, non-deterministic, eval-runtime variability.
  - User-provided sidecar JSON metadata only: too rigid for casual ingest.
- **Rationale**: Frontmatter + filesystem heuristics covers ≥80% of typical knowledge-base content (wikis use frontmatter; SOPs use filename categories). Trivial to test, deterministic, swappable.

## R16. Credential scanner regex catalog

- **Decision**: A static Python module `rag_nano/ingest/credential_scan.py` containing a small list of high-confidence regex patterns:
  - AWS access key: `\bAKIA[0-9A-Z]{16}\b`
  - GitHub PAT: `\bghp_[A-Za-z0-9]{36}\b`
  - Stripe key: `\bsk_live_[A-Za-z0-9]{24,}\b`
  - JWT: `\beyJ[A-Za-z0-9_-]+?\.eyJ[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]+?\b`
  - Generic password assignment: `\b(?:password|api[_-]?key|secret)\s*[:=]\s*["']?[A-Za-z0-9._!@#$%^&*()-]{8,}["']?`
- **Alternatives considered**:
  - `detect-secrets` library: powerful (entropy detection, plugin model), comes with its own config + baseline file workflow; adds dep weight and false-positive surface.
  - `gitleaks` as a subprocess: still a separate binary, awkward for cross-platform local dev.
- **Rationale**: A short, hand-curated regex catalog hits the most common credential types with near-zero false positives and zero dependencies. The contract is "high-confidence patterns only — false negatives are acceptable, false positives are not, because a false positive blocks legitimate ingest". Heavier scanning is a v2 swap (the credential scan is itself a swappable component in spirit, though not enumerated in Constitution V).
- **Trigger to revisit**: the team has a documented credential class not covered by the regex catalog AND a verifiable case where it leaked into the index.

## R17. Eval set storage and metric persistence

- **Decision**:
  - Cases live in `eval/cases.yaml` (one document per case; human-readable diffs).
  - Run history appended to `eval/history.jsonl` (one JSON object per run; append-only; never rewritten).
  - Metric: **recall@k** (default `k=5`) is the v1 primary; `hit_rate` is also computed and stored alongside for free.
- **Alternatives considered**:
  - JSONL for cases: less human-friendly for editing.
  - SQLite for run history: harder to diff and inspect by hand.
- **Rationale**: YAML for human-edited content, JSONL for machine-appended content. Both are git-friendly. recall@k is the most widely-understood retrieval metric and matches the v1 retrieval contract (top-k results). hit_rate (binary: "did expected appear at all") is essentially free to compute and useful as a secondary signal.

## R18. Concurrency model

- **Decision**: FastAPI's default async event loop. Embedding inference runs in a `run_in_executor` thread to avoid blocking the loop. SQLite uses `WAL` mode for concurrent reads during a write. Vector store reloads atomically via "write to temp file then rename".
- **Alternatives considered**:
  - Sync-only (Flask-style): simpler but couples request latency to embedding inference time.
  - Multi-process gunicorn workers: not needed at single-tenant v1 scale.
- **Rationale**: This pattern matches the spec Assumption ("retrieval and ingest may run concurrently … retrieval is never blocked by an ongoing ingest run"). SQLite WAL + atomic-rename of the vector matrix together give MVCC-like read snapshots without a real database.

---

## Selection summary

All 18 selections satisfy Constitution VI (≥2 candidates considered, written rationale). All choices favor:
1. **Local debuggability** — no external services required to run end-to-end.
2. **Minimal dependency surface** — heavy deps only where they replace ≥50 lines of fragile hand-rolled code (sentence-transformers, FastAPI, Pydantic).
3. **Documented upgrade paths** — every "good-enough-for-v1" pick has a named successor and an explicit trigger for promoting it.
