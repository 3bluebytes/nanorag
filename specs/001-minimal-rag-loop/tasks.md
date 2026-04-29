---
description: "Task list for 001-minimal-rag-loop — RAG Nano v1 minimum closed loop"
---

# Tasks: RAG Nano v1 — Minimal Closed Loop (Librarian Layer)

**Input**: Design documents in `specs/001-minimal-rag-loop/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/retrieval-api.md, quickstart.md

**Tests**: REQUIRED. The spec ratifies Constitution X (every retrieval capability needs an evaluation set + script before launch) and Constitution V (every swappable component needs a reference + mock impl proven via tests). All US1/US2/US3 acceptance scenarios become tests.

**Organization**: Tasks are grouped by user story per spec.md (P1 retrieval / P2 ingest / P3 eval) so each story is independently completable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different file, no incomplete-task dependency → safe to do in parallel.
- **[Story]**: `[US1]`, `[US2]`, `[US3]` map to spec.md's prioritized user stories.
- Setup, Foundational, and Polish tasks have no story label.
- Every task names an exact file path or command.

## Path Conventions

Single Python project; package at repo root (`rag_nano/`); tests at `tests/`; eval data at `eval/`. All paths in this file are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and toolchain.

- [X] T001 Create the source-tree skeleton from plan.md: `rag_nano/{api,core,components,ingest,eval,cli}/`, `tests/{contract,integration,unit,fixtures}/`, `eval/`, `scripts/`, `docs/`. Each Python directory gets an empty `__init__.py`.
- [X] T002 Author `pyproject.toml` (PEP 621) declaring Python 3.11+, runtime deps (`fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `sentence-transformers`, `numpy`, `typer`, `pyyaml`, `python-ulid`), dev deps (`pytest`, `pytest-asyncio`, `pytest-mock`, `httpx`, `ruff`, `pyright`), and the `rag-nano` console script entry point. Include `[tool.uv]`, `[tool.ruff]`, `[tool.pyright]` blocks and `[tool.pytest.ini_options]` (asyncio_mode = "auto", testpaths = ["tests"]).
- [X] T003 [P] Create `.env.example` with every variable from quickstart.md's config table commented + default values.
- [X] T004 [P] Create `scripts/download_models.sh` (executable; uses `uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"` to warm the cache) and an empty `scripts/seed_dev_corpus.sh` placeholder (contents added in T038).
- [X] T005 [P] Create `README.md` with one paragraph + a link to `specs/001-minimal-rag-loop/quickstart.md`. Do not duplicate quickstart content.
- [X] T006 Run `uv sync` to materialize `uv.lock`. **Acceptance**: `uv run python -c "import fastapi, sentence_transformers, numpy, typer, pydantic_settings"` exits 0.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Types, Protocols, and the six swappable components. After this phase any user story can be implemented in parallel.

**⚠️ CRITICAL**: No US1/US2/US3 task may begin until Phase 2 is complete (every story imports from this layer).

- [X] T007 [P] Implement `rag_nano/types.py`: `DataType` enum, `RejectionReason` enum, dataclasses for `KnowledgeSource`, `KnowledgeChunk`, `RetrievalResultRecord` (per data-model.md). Keep this file dependency-free (no imports from `rag_nano.components.*`).
- [X] T008 [P] Implement `rag_nano/config.py` with `pydantic_settings.BaseSettings` reading the env vars from quickstart.md (prefix `RAG_NANO_`). Includes typed defaults and a `Settings.from_env()` classmethod.
- [X] T009 [P] Implement `rag_nano/logging_setup.py`: stdlib `logging` configured with a JSON formatter, level from `Settings.log_level`. Single `setup_logging()` entry point.
- [X] T010 [P] Implement `rag_nano/components/protocols.py`: define `EmbeddingProvider`, `VectorStore`, `Retriever`, `MetadataExtractor`, `Reranker`, `StructuredStore` as `typing.Protocol` classes. Each carries the minimum methods used by core/retrieval.py and core/ingest.py (per data-model.md). No concrete imports here.
- [X] T011 [P] Implement `rag_nano/components/embedding.py`: `LocalSentenceTransformerProvider` (loads model from `Settings.embedding_model` lazily, batches encode, normalizes L2, supports the `"query: "` / `"passage: "` prefix convention required by multilingual-e5), `MockEmbeddingProvider` (deterministic hash-based vectors of configurable dim for tests), and `get_embedding_provider(settings) -> EmbeddingProvider` factory selecting on `settings.embedding_backend`.
- [X] T012 [P] Implement `rag_nano/components/vector_store.py`: `NumpyFlatVectorStore` (cosine search via L2-normalized matrix; persistence via the `vectors/{matrix.npy, id_map.json, manifest.json}` layout in data-model.md including the atomic `vectors_next/ → vectors/` rename swap), `InMemoryVectorStore` (no persistence; for tests), and `get_vector_store(settings)` factory.
- [X] T013 [P] Implement `rag_nano/components/retriever.py`: `CosineTopKRetriever` (delegates to a `VectorStore` for the search; applies SQL-side filters via the `StructuredStore`; returns `list[RetrievalResultRecord]`), `MockRetriever` (returns fixture-provided results), and factory.
- [X] T014 [P] Implement `rag_nano/components/reranker.py`: `IdentityReranker` (returns input order unchanged with `rerank_explanation = "identity"`), `MockReranker` (configurable per-test reordering), and factory. v1 ships identity only — body is trivial, interface is real (Constitution IX).
- [X] T015 [P] Implement `rag_nano/components/metadata_extractor.py`: `DefaultMetadataExtractor` (YAML frontmatter for markdown, filename + parent-dir fallback for category, first comment/docstring as fallback summary), `MockMetadataExtractor`, and factory.
- [X] T016 [P] Implement `rag_nano/components/structured_store.py`: `SqliteStructuredStore` (creates the `knowledge_source` and `knowledge_chunk` tables from data-model.md, opens with `PRAGMA journal_mode=WAL`, exposes insert / dedup-by-`(source_path, content_hash)` / query-by-filters / wipe), `InMemoryStructuredStore` (Python dicts; same surface), and factory.
- [X] T017 [P] [tests] `tests/unit/test_embedding.py` — `LocalSentenceTransformerProvider` honors prefix convention; `MockEmbeddingProvider` is deterministic and dim-stable.
- [X] T018 [P] [tests] `tests/unit/test_vector_store.py` — round-trip persistence; cosine top-k correctness on a tiny fixture; atomic-rename swap leaves no half-state observable to a concurrent reader.
- [X] T019 [P] [tests] `tests/unit/test_retriever.py` — filter semantics (any-match within `data_types` and `categories`); k bounds.
- [X] T020 [P] [tests] `tests/unit/test_reranker.py` — identity reranker preserves order and emits `rerank_explanation = "identity"`.
- [X] T021 [P] [tests] `tests/unit/test_metadata_extractor.py` — YAML frontmatter parsing; category fallback chain.
- [X] T022 [P] [tests] `tests/unit/test_structured_store.py` — schema migration is idempotent; `(source_path, content_hash)` UNIQUE blocks duplicates; CASCADE on source delete; WAL mode active after open.
- [X] T023 `tests/integration/test_swappability.py` — **Constitution V gate test**. For every one of the six components, stand up the same minimal end-to-end retrieval flow twice: once wired with reference impls, once wired with mock impls. Both runs MUST produce structurally-equivalent responses (same response shape, same provenance fields populated). Failing this test means the abstraction is leaking.
- [X] T024 [P] `tests/conftest.py` — fixtures: `tmp_index_dir` (cleaned `tmp_path` subdir), `mock_settings` (Settings overridden to use mock backends), `seed_index_fixture` (writes a small set of `KnowledgeSource` + `KnowledgeChunk` records directly through the `StructuredStore` and `VectorStore` Protocols — bypasses the not-yet-built ingest pipeline so US1 can be tested independently of US2). Also: `tests/fixtures/seed_corpus/` populated with: 2 markdown FAQ docs (zh + en), 1 SOP (zh), 1 wiki page (en), 1 code summary file (.py), 1 cold-data sample (raw log), 1 sample with an embedded fake AWS key — used by US2 tests later.

**Checkpoint**: Foundation ready. `pytest tests/unit tests/integration/test_swappability.py` passes; user stories may now begin.

---

## Phase 3: User Story 1 — External agent retrieves explainable knowledge (Priority: P1) 🎯 MVP

**Goal**: HTTP `POST /v1/retrieve` returns ranked, fully-attributed results. `/v1/health` and `/v1/index/stats` answer correctly. The `serve` CLI starts the server.

**Independent Test**: With `seed_index_fixture` populating the index, the contract tests in `tests/contract/test_retrieval_api.py` pass without any ingest code existing yet. Spec acceptance scenarios 1–4 of US1 all green.

### Tests for User Story 1 (write first, expect them to fail before T029-T032)

- [X] T025 [P] [US1] [tests] `tests/contract/test_retrieval_api.py` — exhaustive contract coverage of `POST /v1/retrieve`: the four US1 acceptance scenarios (basic ranked attribution, filter pre-application, debug mode reveals recall+rerank, empty hit list is 200 not error), edge cases (empty query → 422, k out of range → 422, unknown DataType → 422), and FR-005 enforcement (a fixture chunk with cleared `source_id` is dropped, never returned). Uses `httpx.AsyncClient(app=app)` for in-process HTTP.
- [X] T026 [P] [US1] [tests] `tests/integration/test_retrieval_e2e.py` — same four US1 acceptance scenarios, but via the in-process retrieval service (`rag_nano.core.retrieval.retrieve(...)`) bypassing HTTP, to prove the orchestration logic is correct independent of FastAPI plumbing.
- [X] T027 [P] [US1] [tests] `tests/contract/test_health_and_stats.py` — `GET /v1/health` returns `status: ok` with index loaded and `degraded` when no chunks exist; `GET /v1/index/stats` returns a populated `by_data_type` dict + nonzero counts when seeded.
- [X] T028 [P] [US1] [tests] `tests/integration/test_retrieval_provenance_invariant.py` — ranges 100 random queries against a seeded index; asserts every returned hit has all 7 mandatory fields from FR-004 non-empty (Constitution VII gate).

### Implementation for User Story 1

- [X] T029 [US1] Implement `rag_nano/core/retrieval.py` with the orchestrator: `def retrieve(query: RetrievalQuery, components: Components) -> RetrievalResponse`. Pipeline: validate non-empty → embed query → call `Retriever` (which uses `VectorStore` + `StructuredStore` filter pushdown) → call `Reranker` → build response, dropping any record that fails the FR-005 provenance check + logging the drop. When `query.debug` is true, attach the `RetrievalDebugDetail` block from data-model.md. (Depends on T010-T016.)
- [X] T030 [P] [US1] Implement `rag_nano/api/models.py`: Pydantic v2 request/response models exactly matching `contracts/retrieval-api.md`. Include `api_version: Literal["1"]` on every response model.
- [X] T031 [US1] Implement `rag_nano/api/routes.py`: register `POST /v1/retrieve`, `GET /v1/health`, `GET /v1/index/stats` handlers. Each handler is a thin shell that resolves components from the FastAPI dependency container and delegates to `core/retrieval.py` or directly to component reads. Wrap FastAPI's default 422 envelope so it carries the `api_version` field per contract.
- [X] T032 [US1] Implement `rag_nano/api/app.py`: `create_app(settings: Settings) -> FastAPI` factory. Instantiates the six components via factories at startup (single instance per app, shared across requests), attaches them to `app.state`, registers the routes from T031, and wires the FastAPI dependency-injection helpers consumed by T031.
- [X] T033 [US1] Implement the `serve` Typer subcommand in `rag_nano/cli/main.py`: `rag-nano serve [--host 127.0.0.1] [--port 8089]` calls `uvicorn.run(create_app(Settings.from_env()), host=..., port=...)`.

**Checkpoint US1**: `pytest tests/contract tests/integration/test_retrieval_e2e.py tests/integration/test_retrieval_provenance_invariant.py` all green. `uv run rag-nano serve` brings the API up and `curl POST /v1/retrieve` against the seeded fixture returns attributed results. **MVP demoable.**

---

## Phase 4: User Story 2 — Knowledge operator ingests high-value content (Priority: P2)

**Goal**: `rag-nano ingest <path>` runs the full pipeline (load → value-gate → credential-scan → chunk → embed → atomic commit), producing a per-source report. `wipe-index` and `stats` CLI subcommands work.

**Independent Test**: Feed `tests/fixtures/seed_corpus/` (which contains a mix of valid items, one cold-data raw log, and one item with a fake AWS key); verify accepted items are retrievable, rejected items are reported with the right `RejectionReason`, and re-ingesting an unchanged source is a no-op (FR-012).

### Tests for User Story 2 (write first)

- [X] T034 [P] [US2] [tests] `tests/unit/test_value_gate.py` — every supported `DataType` is accepted; every cold-data category in `RejectionReason.cold_data_*` is rejected with the right reason; oversized conversation threshold is enforced (FR-008, FR-009 part a).
- [X] T035 [P] [US2] [tests] `tests/unit/test_credential_scan.py` — each of the 5 regex patterns from research.md R16 fires on a positive sample and does not fire on a curated false-positive sample. Acceptance: zero false positives on a corpus of 100 hand-picked safe lines (FR-009 part b).
- [X] T036 [P] [US2] [tests] `tests/unit/test_chunker.py` — markdown heading-aware split produces ordered chunks with stable position; code line-window with overlap covers 100% of source lines; chunk metadata (`data_type`, `category`) inherited from parent source.
- [X] T037 [P] [US2] [tests] `tests/unit/test_loaders.py` — file extension dispatch matches research.md R13 list; unsupported extension → `RejectionReason.unsupported_format` returned (not raised).
- [X] T038 [P] [US2] [tests] `tests/integration/test_ingest_pipeline.py` — the four US2 acceptance scenarios: (1) batch of valid items becomes retrievable end-to-end; (2) batch with cold + credential items is rejected per-item with reasons; (3) re-ingest of unchanged source is a no-op; re-ingest with new content replaces previous chunks atomically (FR-012); (4) the run report contains accepted / rejected counts and per-data-type breakdown.
- [X] T039 [P] [US2] [tests] `tests/integration/test_concurrent_access.py` — start an ingest run on a thread; concurrently issue retrievals from another thread. Assert: every retrieval observes either the pre-ingest state or the post-ingest state, never a half-committed state. Validates the spec Assumption on concurrent semantics + the atomic-rename swap from data-model.md.
- [X] T040 [P] [US2] [tests] `tests/integration/test_atomic_failure_rollback.py` — induce an embedding failure mid-batch; assert the index reflects either zero of the failing source's chunks or all of them (FR-014), never partial.

### Implementation for User Story 2

- [X] T041 [P] [US2] Implement `rag_nano/ingest/loaders.py`: dispatcher mapping file extension → `RawItem` builder. Markdown loader extracts YAML frontmatter as `original_metadata`. Code loader captures the file's first comment block / docstring as a chunk preamble.
- [X] T042 [P] [US2] Implement `rag_nano/ingest/value_gate.py`: classifies a `RawItem`'s `DataType` from frontmatter (`data_type:`) → operator `--data-type` flag → filename heuristic; rejects cold-data candidates (raw log heuristic, oversized raw conversation threshold from `Settings`, duplicate `(source_path, content_hash)` already in the structured store) with the appropriate `RejectionReason`.
- [X] T043 [P] [US2] Implement `rag_nano/ingest/credential_scan.py`: the 5 regex patterns from research.md R16 compiled at module import; `scan(text) -> RejectionReason | None` returns the first match or `None`.
- [X] T044 [P] [US2] Implement `rag_nano/ingest/chunker.py`: `chunk_markdown(text, settings) -> list[str]` (heading-aware split + recursive char split, sizes from `Settings`), `chunk_code(text, settings) -> list[str]` (line-window with overlap), `chunk(raw_item, settings) -> list[Chunk]` dispatcher that also propagates `data_type`/`category`/`original_metadata` to each child chunk.
- [X] T045 [US2] Implement `rag_nano/ingest/runner.py`: the per-source pipeline `value_gate → credential_scan (per chunk after chunking) → chunker → embed → commit`. Commit is a SQLite transaction wrapping the chunk inserts plus an atomic vector-dir rename. On any failure mid-source, the transaction rolls back AND the staged `vectors_next/` is removed; the source's pre-existing chunks remain intact. Returns an `IngestRunReport` (counts + per-item rejection reasons + per-data-type breakdown).
- [X] T046 [US2] Implement `rag_nano/core/ingest.py`: top-level `ingest(paths: list[Path], components: Components, settings: Settings) -> IngestRunReport`. Walks the input paths, dispatches to `loaders.py`, drives `runner.py` per source, aggregates the report. Used by both the CLI and (future) HTTP ingest.
- [X] T047 [US2] Implement the `ingest` Typer subcommand in `rag_nano/cli/main.py`: `rag-nano ingest <paths…> [--data-type X] [--category Y]`. Renders the `IngestRunReport` as a human-readable terminal summary (per-source line + final block).
- [X] T048 [US2] Implement the `wipe-index` and `stats` Typer subcommands. `wipe-index` requires `--yes` or interactive confirmation (FR scope decision); deletes the SQLite file + the `vectors/` directory. `stats` prints the same payload `GET /v1/index/stats` returns.
- [X] T049 [US2] Replace the direct-write seed in `tests/conftest.py:seed_index_fixture` with a fixture variant `seed_index_via_ingest_fixture` that drives the real ingest pipeline on `tests/fixtures/seed_corpus/`. Both fixtures coexist; US1 tests keep using the direct-write seed (story-independence guarantee), US2/US3 tests use the via-ingest seed.
- [X] T050 [US2] Fill in `scripts/seed_dev_corpus.sh`: runs `uv run rag-nano ingest tests/fixtures/seed_corpus/` against a fresh index. Used by the quickstart "what v1 done looks like" smoke script.

**Checkpoint US2**: `pytest tests/unit tests/integration/test_ingest_pipeline.py tests/integration/test_concurrent_access.py tests/integration/test_atomic_failure_rollback.py` green. `uv run rag-nano ingest tests/fixtures/seed_corpus/` produces the expected accept/reject report; subsequent retrieval against the freshly-built index returns attributed results.

---

## Phase 5: User Story 3 — Developer measures retrieval quality (Priority: P3)

**Goal**: `rag-nano eval` runs all cases in `eval/cases.yaml`, computes recall@k + hit_rate, appends a record to `eval/history.jsonl`, and prints the metric and its delta vs. the previous run.

**Independent Test**: With an ingested fixture corpus and a hand-curated 20-case `eval/cases.yaml`, `rag-nano eval` produces a numeric metric in one shot, and a second run with no code changes shows zero delta.

### Tests for User Story 3 (write first)

- [X] T051 [P] [US3] [tests] `tests/unit/test_metrics.py` — recall@k correctness on toy fixtures (perfect retrieval = 1.0, miss = 0.0, partial = expected fraction); hit_rate correctness; both metrics handle empty results gracefully.
- [X] T052 [P] [US3] [tests] `tests/unit/test_eval_history.py` — `append(run)` produces a single JSONL line; `previous_run()` returns the most recent prior record or `None`; `compare(current, previous)` produces the right `delta_vs_previous` block.
- [X] T053 [P] [US3] [tests] `tests/integration/test_eval_pipeline.py` — the three US3 acceptance scenarios: (1) full eval set runs in one command and emits a metric; (2) consecutive runs surface the metric delta visibly; (3) updating the eval set is reflected without code changes. Plus FR-021 coverage: a single broken case (expected chunk_id no longer in the index) is flagged in the per-case outcome but does NOT abort the run.
- [X] T054 [P] [US3] [tests] `tests/unit/test_eval_composition_validator.py` — the eval runner's startup composition check (≥20 cases, ≥1 case per data type appearing in the corpus, ≥1 zh + ≥1 en) raises a clear error if violated.

### Implementation for User Story 3

- [X] T055 [P] [US3] Implement `rag_nano/eval/metrics.py`: `recall_at_k(actual: list[str], expected: list[str], k: int) -> float`, `hit_rate(actual: list[str], expected: list[str]) -> float`. Pure functions, no I/O.
- [X] T056 [P] [US3] Implement `rag_nano/eval/history.py`: `append(run: EvaluationRun, path: Path)`, `previous_run(path: Path) -> EvaluationRun | None`, `compare(current, previous) -> dict | None`. Append-only file; never rewrite.
- [X] T057 [US3] Implement `rag_nano/eval/runner.py`: load `cases.yaml`, run the composition validator, for each case call `core.retrieval.retrieve(...)` in-process, compute per-case outcome (`chunk_ids` mode = expected_chunk_ids subset of returned chunk_ids; `substring` mode = expected substring appears in any returned chunk's text), aggregate into an `EvaluationRun`, append to history, print summary + delta. Per FR-021 a per-case failure is flagged in the run record but does not abort the run.
- [X] T058 [P] [US3] Create `eval/cases.yaml` with **20 placeholder-but-structurally-valid cases**: ≥1 per data type that exists in `tests/fixtures/seed_corpus/` (faq, sop, wiki, code_summary), ≥10 zh queries + ≥10 en queries; mix `chunk_ids` and `substring` modes. Document at the top of the file: "These are seed cases — replace with real curated cases as the corpus grows."
- [X] T059 [P] [US3] Create `eval/README.md` documenting the case schema (link to data-model.md `EvaluationCase`) and the composition rules from spec.md Assumptions.
- [X] T060 [US3] Implement the `eval` Typer subcommand in `rag_nano/cli/main.py`: `rag-nano eval [--k 5] [--out -] [--fail-on-regression]`. `--fail-on-regression` flips the exit code to 1 when `recall_delta < 0`. Otherwise exit code is 0 even when individual cases fail (per FR-021).

**Checkpoint US3**: `pytest tests/unit/test_metrics.py tests/unit/test_eval_history.py tests/unit/test_eval_composition_validator.py tests/integration/test_eval_pipeline.py` green. `uv run rag-nano eval` runs against the seeded corpus, prints `recall@5 = …` and `delta vs previous = …`, and writes to `eval/history.jsonl`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Constitution VIII proof points, end-to-end smoke validation, lint/type pass, README polish.

- [X] T061 [P] `tests/integration/test_agent_integration_chat.py` — drives Example A from quickstart.md against a live in-process app: a simulated chat agent posts a question, gets results, formats them with citations, and asserts the formatted answer carries source paths. **Constitution VIII proof point #1.**
- [X] T062 [P] `tests/integration/test_agent_integration_workflow.py` — drives Example B from quickstart.md: a simulated workflow agent processes a JSONL of issues, looks up SOP+FAQ chunks via the retrieval API with `data_types` filter, asserts each output line has a populated `librarian_top_k` block. **Constitution VIII proof point #2.**
- [X] T063 Wire the top-level Typer app in `rag_nano/cli/main.py` (`app = typer.Typer()`; `@app.callback()` for global options; register subcommands `ingest`, `serve`, `eval`, `wipe-index`, `stats`) and the `[project.scripts] rag-nano = "rag_nano.cli.main:app"` entry point in `pyproject.toml`. Verify `uv run rag-nano --help` lists all five subcommands.
- [X] T064 [P] Run `ruff check rag_nano tests` and `ruff format --check rag_nano tests` — fix any findings. Run `pyright rag_nano` — fix any type errors. **Acceptance**: zero lint warnings, zero pyright errors.
- [X] T065 Execute the entire "what v1 done looks like" smoke script from `quickstart.md` end-to-end on a fresh checkout. Re-run the same script a second time and confirm the eval metric reproduces within the documented tolerance — proves **SC-007 (reproducibility)**. Capture any deviations as new tasks.
- [X] T066 Final README.md pass — confirm it points to `specs/001-minimal-rag-loop/quickstart.md` and contains nothing that would rot when the spec evolves.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: T006 depends on T002. T003/T004/T005 [P] can run alongside T002. T001 first.
- **Phase 2 (Foundational)**: All tasks depend on Phase 1 completion. T007/T008/T009/T010 [P] are independent. T011-T016 each depend on T010 (Protocols). T017-T022 unit tests depend on their respective component impls. T023 (swappability gate) depends on all of T011-T016. T024 (conftest) depends on T010 + at least one mock impl per component (T011-T016).
- **Phase 3 (US1)**: All tasks depend on Phase 2 (Checkpoint). Tests T025-T028 [P] are written before implementation T029-T033 and expected to fail. T030 [P] is independent of T029. T031 depends on T030 + T029. T032 depends on T031. T033 depends on T032.
- **Phase 4 (US2)**: All tasks depend on Phase 2. Independent of US1 in source — both can be developed in parallel by separate developers. Within US2: T041-T044 [P] are independent. T045 depends on T041-T044. T046 depends on T045. T047/T048 depend on T046. T049/T050 depend on T046+T047. Tests T034-T040 [P] written before their corresponding impls.
- **Phase 5 (US3)**: All tasks depend on Phase 2. Independent of US1 in source; depends on US2's seeded fixture for end-to-end tests (use `seed_index_via_ingest_fixture` from T049). T055-T056 [P] are independent. T057 depends on T055+T056. T058/T059 [P] are independent of code. T060 depends on T057.
- **Phase 6 (Polish)**: T061/T062 depend on US1 + US2 done (need real ingested index to query). T063 depends on US1 + US2 + US3 (registers all five subcommands). T064 [P] can run anytime there is code to lint. T065 depends on T063. T066 [P] is independent.

### Within Each User Story

- Tests written first; implementation makes them pass.
- Models / types before services; services before HTTP/CLI surface.
- Component impl before tests that depend on the impl as a fixture.
- Story complete (all tests green at its checkpoint) before moving to the next priority.

### Parallel Opportunities

- All Phase 1 [P] tasks can run together after T002.
- All six component implementations (T011-T016) can be developed in parallel after T010.
- All six component unit tests (T017-T022) can be written in parallel.
- US1 and US2 can be developed in parallel by different developers after Phase 2.
- US3 can begin in parallel with the tail of US2 (US3 only blocks at T057's first run, which needs US2's atomic-commit ingest landed).
- Within each story, all `[P]` tasks (typically test files + independent implementation files) can run together.

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After T010 (Protocols) lands, fan out the six components in parallel:
Task: "Implement rag_nano/components/embedding.py per T011"
Task: "Implement rag_nano/components/vector_store.py per T012"
Task: "Implement rag_nano/components/retriever.py per T013"
Task: "Implement rag_nano/components/reranker.py per T014"
Task: "Implement rag_nano/components/metadata_extractor.py per T015"
Task: "Implement rag_nano/components/structured_store.py per T016"

# Then fan out their unit tests in parallel:
Task: "Write tests/unit/test_embedding.py per T017"
Task: "Write tests/unit/test_vector_store.py per T018"
Task: "Write tests/unit/test_retriever.py per T019"
Task: "Write tests/unit/test_reranker.py per T020"
Task: "Write tests/unit/test_metadata_extractor.py per T021"
Task: "Write tests/unit/test_structured_store.py per T022"
```

## Parallel Example: User Story 2

```bash
# After Phase 2, fan out the four pipeline pieces in parallel:
Task: "Implement rag_nano/ingest/loaders.py per T041"
Task: "Implement rag_nano/ingest/value_gate.py per T042"
Task: "Implement rag_nano/ingest/credential_scan.py per T043"
Task: "Implement rag_nano/ingest/chunker.py per T044"

# Tests can be written in parallel with implementations:
Task: "Write tests/unit/test_value_gate.py per T034"
Task: "Write tests/unit/test_credential_scan.py per T035"
Task: "Write tests/unit/test_chunker.py per T036"
Task: "Write tests/unit/test_loaders.py per T037"
```

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2 + Phase 3 only)

1. Phase 1 (Setup) — pyproject + skeleton.
2. Phase 2 (Foundational) — types, Protocols, six components with reference + mock + factory, swappability gate test.
3. Phase 3 (US1) — HTTP retrieval API; tested via direct-write seed fixture.
4. **STOP and validate**: `pytest tests/unit tests/contract tests/integration/test_swappability.py tests/integration/test_retrieval_e2e.py tests/integration/test_retrieval_provenance_invariant.py` green; `curl POST /v1/retrieve` returns attributed results from the seed fixture.

This is the demonstrable MVP — the librarian API works against a hand-seeded index, proving the contract is real before any pipeline code is written. Note: this MVP does NOT yet satisfy Constitution X (no eval set yet) or the full spec (no real ingest yet) — those are Phase 4/5 deliverables. But the public contract is real and exercisable.

### Incremental Delivery

1. MVP (Setup → Foundational → US1).
2. Add US2 → swap fixture seed for real ingest; cold-data + credential gates verified end-to-end.
3. Add US3 → eval harness + 20-case seed; recall@k baseline established.
4. Polish (Constitution VIII proof tests + smoke + lint + reproducibility check) → v1 shippable.

Each increment leaves the system in a green-test state.

### Parallel Team Strategy

With multiple developers:

1. Together: Phase 1 + Phase 2.
2. After Phase 2:
   - Dev A: US1 (retrieval HTTP path)
   - Dev B: US2 (ingest pipeline)
   - Dev C: US3 setup work (cases.yaml, metrics, history) — eval runner blocks on US2's atomic ingest landing.
3. Together: Phase 6 polish + smoke.

---

## Notes

- **[P] = different file, no dependency on an incomplete task** — safe to run concurrently.
- **[US#] = traceability** to the user story this task delivers; preserved in commit messages by `/speckit-implement`.
- Each acceptance criterion in this file maps back to a spec FR or US scenario; no orphan tasks.
- Commit cadence (per the autonomous flow agreement): one commit per logical task group (typically one phase or one parallel cluster), `[Spec Kit] [US#]` prefix.
- A failed test at any checkpoint is a hard stop — fix the underlying issue rather than skipping the test or weakening the assertion.
- v1 reranker is intentionally `IdentityReranker`; the `tests/unit/test_reranker.py` test covers the trivial body but the *interface* is exercised by `tests/integration/test_swappability.py` and the contract debug-mode tests — proving the abstraction is real, not vestigial.

## Traceability Map (FR / SC ↔ Tests)

| Spec ref | Verifying task(s) |
|----------|-------------------|
| FR-001 (single agent-neutral retrieval entry) | T025, T029, T032 |
| FR-002 (data_type + category filters) | T025, T013, T019 |
| FR-003 (k bounds) | T025 |
| FR-004 (every result attributed) | T025, T028, T031 |
| FR-005 (no untraceable result) | T025 (FR-005 case), T029 (drop-and-log) |
| FR-006 (debug mode) | T025, T029 |
| FR-007 (no results ≠ error) | T025 |
| FR-008 (data type whitelist) | T034, T042 |
| FR-009 (cold + credential rejection) | T034, T035, T038, T042, T043 |
| FR-010 (chunks persisted to vector + structured) | T038, T045 |
| FR-011 (chunk traceability to source) | T028, T038 |
| FR-012 (no duplicate sources) | T038 (re-ingest scenario), T022 (UNIQUE constraint) |
| FR-013 (per-run report) | T038, T045, T047 |
| FR-014 (atomic per-source) | T040, T045 |
| FR-015 (six components are Protocol-defined) | T010, T023 |
| FR-016 (ref + mock per component) | T011-T016, T023 |
| FR-017 (reranker interface present) | T014, T020, T023, T029 |
| FR-018 (≥20 eval cases) | T058, T054 |
| FR-019 (one-command eval) | T053, T060 |
| FR-020 (history + delta) | T052, T053, T056 |
| FR-021 (per-case failure does not abort) | T053, T057 |
| FR-022 (scope guard — nothing extra in v1) | reviewed in T065 smoke pass |
| SC-001 (external integration in 1 day) | T061, T062, T065 |
| SC-002 (every hit fully attributed, automated) | T028 |
| SC-003 (≥20 cases, single metric per run) | T058, T053 |
| SC-004 (regression detectable in 1 command) | T060 |
| SC-005 (swappability proven by tests) | T023 |
| SC-006 (cold-data rejection reasons reported) | T034, T038 |
| SC-007 (reproducibility: same metric on fresh checkout) | T065 |
| Constitution VIII (≥2 agent integration examples) | T061, T062 |
