# Feature Specification: RAG Nano v1 — Minimal Closed Loop (Librarian Layer)

**Feature Branch**: `001-minimal-rag-loop`
**Created**: 2026-04-27
**Status**: Draft
**Input**: User description: "RAG Nano 第一版（书库管理员层）。本仓库 rag-nano 只实现书库管理员——一个独立、与任何 agent 解耦的 RAG 服务。第一版交付 ingest（数据摄取）+ retrieval（知识检索）+ evaluation（效果评测）三条主链路，暴露稳定的 agent‑neutral 检索接口供外部 orchestrator 调用。"

## Clarifications

### Session 2026-04-27

- Q: Where does v1 produce embeddings — hosted API, local model, or both? → A: Local multilingual model only in v1 (e.g. BGE-m3 / multilingual-e5; concrete model fixed in plan.md). The embedding component sits behind a stable provider contract (Protocol/ABC + factory pattern); a hosted-API backend or any additional production implementation can be added later as a pure-additive new class — no changes required in retrieval, ingest, or evaluation consumers. Same swappable pattern applies uniformly to all six core components (embedding, vector store, retriever, metadata extractor, reranker, structured store).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - External agent retrieves explainable knowledge (Priority: P1)

An external orchestrator (the "front-desk receptionist") has decided that short-term memory does not satisfy the user's question, and dispatches the query to the librarian (this system) as a "work order". The librarian returns a small ranked list of knowledge results. Every result is fully attributed: the orchestrator can show the source, decide whether the answer is trustworthy, and quote it back to the end user with provenance.

**Why this priority**: The retrieval contract is the only thing external consumers see. If retrieval is broken or unattributed, no other capability matters. Without retrieval, the system has no public surface and delivers zero value.

**Independent Test**: Seed the index with a small fixture of curated content. Issue a query through the public retrieval interface. Verify the response shape contains source identifier, score, data type, category, and original metadata for every hit. The test passes without involving any agent, ingest pipeline, or evaluation infrastructure.

**Acceptance Scenarios**:

1. **Given** a knowledge base seeded with curated chunks, **When** the caller submits a non-empty query, **Then** the system returns up to k hits, each carrying a source identifier, a relevance score, a data-type label, a category label, and the original metadata captured at ingest.
2. **Given** the caller passes a filter (e.g. `data_type = "FAQ"`), **When** the query runs, **Then** every returned hit matches the filter; hits that would have been returned without the filter are excluded from the response.
3. **Given** the caller enables debug mode, **When** the query runs, **Then** the response additionally exposes (a) the candidate recall list before reranking and (b) the reranker's per-candidate decision detail.
4. **Given** a query that yields no candidates passing the filter or relevance threshold, **When** the query runs, **Then** the system returns an empty hit list with an unambiguous "no results" status, not an error.

---

### User Story 2 - Knowledge operator ingests high-value content (Priority: P2)

A knowledge operator wants to add a batch of high-value content (FAQs, SOPs, post-mortem summaries, configuration notes, structured knowledge cards) to the librarian's index. They submit the batch through the ingest pipeline and receive a clear report of what was accepted, what was rejected, and why. Cold data (raw logs, full source dumps, raw transcripts, oversized duplicates) is rejected at the gate — it cannot enter the main index without first being summarized/structured externally.

**Why this priority**: Without ingest the index is empty and retrieval has nothing to return. But the retrieval contract (P1) can be exercised against a fixture index, so ingest can land second without blocking interface work.

**Independent Test**: Provide a directory mixing clearly high-value items and clearly cold-data items. Run the ingest command. Verify (a) the high-value items become retrievable through the public retrieval interface, (b) the cold-data items are rejected with a per-item reason, (c) every ingested chunk is traceable to its original source.

**Acceptance Scenarios**:

1. **Given** a batch of items declared as one of the supported high-value data types, **When** ingest runs, **Then** every accepted item is split into chunks, embedded, and persisted such that it is retrievable via the public retrieval interface and traceable back to its source.
2. **Given** a batch containing items flagged as cold data (raw logs, raw transcripts, files exceeding a configured size threshold without a prior summary card), **When** ingest runs, **Then** those items are rejected before reaching the index and the run report shows a per-item reason.
3. **Given** the same source is re-ingested, **When** ingest runs again, **Then** the system either skips it or replaces its previous chunks; duplicate insertion of the same source does not occur.
4. **Given** a successful ingest run, **When** the operator inspects the report, **Then** they can see counts of accepted/rejected items, total chunks produced, and a per-data-type breakdown.

---

### User Story 3 - Developer measures retrieval quality (Priority: P3)

A developer changes any part of the retrieval stack (chunking, embedding, retriever, reranker). Before merging the change, they run the evaluation harness with a single command. They see at least one quantitative metric (e.g. recall@k) over the curated query set, can compare it to the previous run, and can decide whether the change is a regression.

**Why this priority**: Constitution X requires an evaluation set and metric before launch. The team can prototype P1 and P2 before the harness lands, but evaluation must exist before the librarian is considered shippable. Building the harness third lets it land on top of working ingest+retrieval rather than running ahead of either.

**Independent Test**: With ingest + retrieval already working, populate the evaluation set with at least 20 query→expected-result pairs. Run the evaluation script. Verify it produces a numeric metric and writes a versioned record so the next run can compare.

**Acceptance Scenarios**:

1. **Given** an evaluation set of at least 20 query→expected-result pairs, **When** the developer runs the evaluation script, **Then** the script emits at least one metric computed over the full set in a single run, with no manual intervention.
2. **Given** evaluation has been run before, **When** the developer runs it again after a code change, **Then** the script reports the new metric alongside the previous result so a regression is immediately visible.
3. **Given** the evaluation set is updated (a query added or an expected result revised), **When** the script runs, **Then** the new state of the eval set is reflected in the output without requiring code changes elsewhere.

---

### Edge Cases

- Query is empty or whitespace-only → rejected with a clear error before any retrieval cost is incurred.
- Query yields zero candidates after filtering → empty hit list with "no results" status, not an error.
- Retrieval is invoked while the index is empty (fresh checkout, before any ingest) → empty hit list with an indication that the index has no content; system does not crash.
- Ingest receives a file in a format not supported by v1 → per-item rejection with a clear reason; partial inserts are not allowed.
- Ingest receives a chunk whose embedding fails (provider error) → the run reports the failure and either skips that item or aborts the batch atomically; the index must never be left in a partially-poisoned state.
- A core component (vector store, embedding) is swapped to its mock implementation → retrieval still functions and tests still pass, proving the abstraction holds.
- Eval set contains a query whose expected result was deleted from the index → the harness flags the case and continues; one bad case must not abort the whole run.
- Two distinct ingest sources happen to produce identical chunk text → both are retained, but each must remain individually traceable to its source.

## Requirements *(mandatory)*

### Functional Requirements

**Retrieval interface (public contract)**

- **FR-001**: System MUST expose a single, agent-neutral retrieval entry point through which an external caller submits a query string and receives a ranked list of knowledge results. The contract MUST NOT include any agent-specific prompt template, dialogue format, or business logic.
- **FR-002**: System MUST accept optional retrieval filters covering at minimum data type and category, applied before the response is returned.
- **FR-003**: System MUST allow the caller to specify the number of results (k) per query, with a documented default and a documented maximum.
- **FR-004**: Every retrieval result returned to the caller MUST include: source identifier, relevance score, data-type label, category label, and the original metadata captured at ingest.
- **FR-005**: System MUST refuse to return any result that lacks a verifiable source identifier; results without traceable provenance MUST NOT reach the caller.
- **FR-006**: System MUST provide a debug mode in which the response additionally exposes (a) the candidate recall list before reranking and (b) the reranker's per-candidate detail used to produce the final order.
- **FR-007**: System MUST distinguish "no matching results" from "error" in the retrieval response; an empty match set is a valid, non-error outcome.

**Ingest pipeline**

- **FR-008**: System MUST accept ingest only for the following high-value data types: documents, FAQs, SOPs, historical case write-ups, issue summaries, wiki pages, configuration notes, structured knowledge cards, code summaries, log summaries.
- **FR-009**: System MUST reject ingest items at the gate when they either (a) fall under cold-data categories (raw logs, full raw source dumps, raw execution traces, oversized raw conversations, duplicate raw documents), or (b) match high-confidence credential patterns (e.g. AWS access keys, JWT tokens, GitHub personal access tokens, generic `password=` / `api_key=` / `secret=` assignments). Each rejected item MUST be reported with a per-item reason in the run report.
- **FR-010**: System MUST split accepted items into retrievable chunks, attach metadata (source, data type, category, ingest timestamp), and persist them to vector storage and structured storage.
- **FR-011**: System MUST tag every chunk with a stable identifier traceable back to a single source so that any chunk surfaced by retrieval can be traced to its origin.
- **FR-012**: System MUST handle re-ingest of the same source by either skipping it or replacing its previous chunks; duplicate insertion of the same source MUST NOT occur.
- **FR-013**: System MUST produce a per-run ingest report listing at minimum: count of accepted items, count of rejected items with per-item reasons, total chunks produced, and a per-data-type breakdown.
- **FR-014**: System MUST fail an ingest run atomically if the failure would leave the index in an inconsistent state with respect to a single source; partial source ingestion that cannot be cleanly rolled back is not allowed.

**Component abstraction (Constitution V)**

- **FR-015**: System MUST define each of the following as a swappable component behind a stable contract: embedding generator, vector store, retriever, metadata extractor, reranker, structured store. Business logic MUST NOT depend on any specific provider's API surface or query syntax.
- **FR-016**: System MUST ship at least one reference implementation and one test/mock implementation for every component named in FR-015. Switching between them MUST NOT require changes outside that component's wiring.
- **FR-017**: The reranker MAY be a pass-through (identity) or a minimal cross-encoder body in v1; the interface MUST be present and exercised even when the body is trivial.

**Evaluation harness**

- **FR-018**: System MUST maintain a versioned evaluation set of at least 20 query→expected-result pairs.
- **FR-019**: System MUST provide a single command that runs the entire evaluation set against the current configured retrieval stack and emits at least one numeric metric (recall@k, hit rate, or precision@k).
- **FR-020**: Evaluation runs MUST persist their results to a history allowing comparison against the previous run; a single regression must be observable without manual diffing.
- **FR-021**: A per-case failure in the evaluation set (e.g. expected result missing from the index) MUST NOT abort the run; the case MUST be flagged in the output and the rest of the run MUST complete.

**Bounded scope (Constitution IX)**

- **FR-022**: System MUST NOT implement any of the following in v1: multi-agent orchestration, conversation/short-term memory, complex front-end UI, graph database integration, message queues, multi-tenant access control, multimodal ingestion. Where any of these is touched at all, only the interface placeholder or TODO is allowed.

### Key Entities

- **KnowledgeSource**: Origin of a piece of ingested content (file, URL, structured card). Carries source identifier, data type, category, ingest timestamp, value-assessment outcome.
- **KnowledgeChunk**: Retrievable unit produced from a KnowledgeSource. Carries chunk identifier, parent source identifier, text payload, embedding reference, inherited data type and category, original metadata.
- **RetrievalQuery**: Inbound query as received via the public contract. Carries query text, optional filters, optional k, optional debug flag.
- **RetrievalResult**: One ranked hit returned to the caller. Carries chunk identifier, source identifier, relevance score, data type, category, original metadata, and (in debug mode) per-candidate recall/rerank detail.
- **EvaluationCase**: One entry in the evaluation set. Carries query text, expected-hit identifiers (or expected-result rule), optional notes.
- **EvaluationRun**: One execution of the evaluation harness. Carries timestamp, configuration snapshot reference, per-case outcomes, computed metric(s), comparison against the previous run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An external caller, given only the public retrieval interface documentation and no internal access, can integrate against the librarian and receive correctly attributed results within one working day of starting integration.
- **SC-002**: Every retrieval result returned to a caller carries source, score, data type, category, and original metadata — verified by an automated check that fails if any field is missing on any hit, across the full evaluation set.
- **SC-003**: The first version of the evaluation set contains at least 20 query→expected-result pairs and produces a single quantitative metric on every run.
- **SC-004**: A retrieval-stack code change can be classified as "regression" or "non-regression" by running one command, with no manual computation of metrics.
- **SC-005**: Each of the six core components named in FR-015 has a working reference implementation and a working mock implementation; the test suite proves swappability by passing under both wirings.
- **SC-006**: Any item rejected by the cold-data gate during ingest is reported with a specific reason in the run report — verified by feeding fixtures of known cold data and checking that rejection reasons appear.
- **SC-007**: Once the index is built from a fixed corpus, a fresh checkout of the repository can reproduce the same evaluation metric within a tolerance documented in the eval harness — proving the librarian is reproducible end-to-end without hidden state.

## Assumptions

- The orchestrator and the short-term memory layer are owned by other projects. This repository delivers only the librarian; the orchestrator's "query memory first, dispatch to librarian on miss" policy is out of scope.
- Document language scope for v1 is mixed Chinese + English. The embedding stack MUST support both languages in a single model (multilingual embedding); using a monolingual model tuned for only one side is out of scope.
- Embedding backend for v1 is a single local multilingual model loaded via a sentence-transformers-compatible loader (concrete model fixed in plan.md). The embedding component is defined behind a stable provider contract; adding hosted-API or any additional production backend later is a pure-additive new implementation of the same contract — no changes required in retrieval, ingest, or evaluation consumers. The same swappable contract pattern applies uniformly to vector store, retriever, metadata extractor, reranker, and structured store.
- The retrieval interface form for v1 is an HTTP API served by a local server (single deliverable). An in-process SDK form is NOT built in v1; downstream consumers that prefer in-process access wrap the HTTP client themselves.
- HTTP retrieval responses carry an `api_version` field. v1 emits `"1"`. Backwards-incompatible response shape changes increment this value; backwards-compatible additions do not.
- Ingest input formats for v1 are: plain text, Markdown, and source-code files (a defined list of languages such as .py / .ts / .js / .go / .java / .rs — exact set to be finalized in plan.md). HTML, PDF, office documents, and binary attachments are out of scope and rejected at the ingest gate.
- Ingest applies a regex-based credential scan at the gate using canonical patterns (AWS access keys, JWT tokens, GitHub personal access tokens, generic `password=` / `api_key=` / `secret=` assignments, etc.). Items matching high-confidence patterns are rejected with a per-item reason (per FR-009). PII scrubbing (names, emails, national IDs) is NOT in v1 and remains an external pre-processing concern per Constitution IV (cold-data prohibition).
- Operator scale for v1 is single-developer, local workstation, single-tenant. No authentication, authorization, or quota system is in scope.
- v1 corpus is sized for up to ~5,000 source documents and ~50,000 chunks on a single workstation. Beyond this scale, a different vector store backend is expected to be swapped in via the contract from Constitution V; no v1 consumer changes are required for the swap.
- Latency target for v1 is "interactive for a developer" — sub-2-second per retrieval call on the reference local setup. Higher-throughput or production-grade SLOs are out of scope.
- Retrieval and ingest may run concurrently. Each ingest source's chunks are committed atomically: until commit, retrieval sees the pre-ingest state for that source. Retrieval is never blocked by an ongoing ingest run.
- Re-indexing strategy for v1 is full-source replace on re-ingest. Incremental delta indexing is out of scope.
- Operator can wipe the entire index (vector store + structured store) via a single CLI subcommand; the operation is destructive and prompts for confirmation. No partial-wipe by data type or source is in v1 — use re-ingest per FR-012 instead.
- The evaluation set lives in version control alongside the code. Treating eval cases as production data with their own lifecycle is out of scope for v1.
- Evaluation set composition rules for v1: (a) at least 20 cases per FR-018; (b) the set MUST collectively span every v1 high-value data type that appears in the corpus; (c) the set MUST include both Chinese and English queries. Curation is the eval owner's responsibility; the harness enforces only structural requirements (case count + metadata presence), not topical coverage.
- The librarian is invoked synchronously by callers in v1. Async/streaming retrieval modes are out of scope.
