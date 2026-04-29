# rag-nano

> 中文版傻瓜指南：[`README_zh.md`](README_zh.md)

Minimum closed-loop librarian for RAG-driven assistants. An external agent (chat agent, workflow agent, batch job) dispatches a query and gets back ranked, fully-attributed knowledge chunks over a stable HTTP contract.

The librarian is **agent-neutral**: it owns retrieval + provenance only. Prompt construction, dialogue history, answer generation, short-term memory live elsewhere.

Canonical design + full contract: [`specs/001-minimal-rag-loop/`](specs/001-minimal-rag-loop/) — see `quickstart.md`, `spec.md`, `contracts/retrieval-api.md`.

---

## Install

```bash
uv sync
uv run scripts/download_models.sh   # ~2.3 GB embedding model, first time only
cp .env.example .env                  # optional; defaults work
```

## Daily commands

```bash
uv run rag-nano ingest <path-or-dir>           # add knowledge
uv run rag-nano serve [--port 8089]            # start HTTP API
uv run rag-nano eval [--fail-on-regression]    # measure quality
uv run rag-nano stats                          # snapshot
uv run rag-nano wipe-index --yes               # destructive reset
```

`ingest` pipeline: load → value-gate (rejects raw logs / oversized conversations) → credential scan (AWS / GitHub / Stripe / JWT / generic secrets) → chunk → embed → atomic commit (SQLite + atomic `vectors_next/ → vectors/` rename). Re-ingesting an unchanged source is a no-op; new content atomically replaces previous chunks.

## Inspecting the knowledge base

### High-level snapshot

```bash
uv run rag-nano stats
# Chunk count:  10
# Source count: 5
# By data_type:
#   faq: 4
#   sop: 3
#   wiki: 2
#   code_summary: 1
# Last ingest: 2026-04-28T20:44:44+00:00
```

Same payload via HTTP (when `serve` is running):

```bash
curl -s http://127.0.0.1:8089/v1/index/stats | jq
```

### List every ingested source

```bash
sqlite3 .rag-nano/structured.db -box \
  "SELECT source_path, data_type, category, chunk_count, ingested_at
   FROM knowledge_source ORDER BY ingested_at DESC;"
```

### Inspect chunks of a specific source

```bash
sqlite3 .rag-nano/structured.db -box \
  "SELECT position, substr(text, 1, 80) AS preview
   FROM knowledge_chunk
   WHERE source_id = (
     SELECT source_id FROM knowledge_source
     WHERE source_path = 'tests/fixtures/seed_corpus/sop_hotfix_zh.md'
   )
   ORDER BY position;"
```

### Probe coverage with a real query

```bash
curl -s -X POST http://127.0.0.1:8089/v1/retrieve \
     -H 'content-type: application/json' \
     -d '{"query":"your topic here","k":5}' \
  | jq '.results[] | {source_path, data_type, score}'
```

Empty or off-topic results → corpus is thin in that area; ingest more.

## HTTP API

`POST /v1/retrieve` — main endpoint:

```json
{
  "query": "how to deploy a hotfix",
  "k": 5,
  "filters": {"data_types": ["sop", "faq"], "categories": []},
  "debug": false
}
```

Returns ranked `results[]`; every hit carries `chunk_id`, `source_id`, `source_path`, `score`, `data_type`, `category`, `text`, `original_metadata`. No untraceable result is ever returned (FR-005).

`GET /v1/health`, `GET /v1/index/stats` — diagnostics. Full schema: [`specs/001-minimal-rag-loop/contracts/retrieval-api.md`](specs/001-minimal-rag-loop/contracts/retrieval-api.md).

## Integration patterns

Two reference patterns, both exercised by integration tests against the live HTTP path:

- **Chat agent** — agent renders chunks with citations into a reply. See [`tests/integration/test_agent_integration_chat.py`](tests/integration/test_agent_integration_chat.py).
- **Workflow agent** — batch job filters by `data_types` and embeds top-k into JSONL output. See [`tests/integration/test_agent_integration_workflow.py`](tests/integration/test_agent_integration_workflow.py).

The agent owns prompts, dialogue state, and rendering. The librarian only returns attributed chunks.

## Evaluation

Cases live in [`eval/cases.yaml`](eval/cases.yaml). Edit the file — no code change needed — then rerun:

```bash
uv run rag-nano eval
# recall@5 = 0.8500
# hit_rate    = 0.8500
# cases       = 20
# delta vs previous: recall +0.0000, hit_rate +0.0000
```

Each run appends one record to `eval/history.jsonl` (gitignored; operator-side state). Composition rules (≥20 cases, ≥1 per data_type in the corpus, ≥1 zh + ≥1 en) are enforced at startup.

## Configuration

`.env` overrides; full table in `specs/001-minimal-rag-loop/quickstart.md`. Most-used:

| Variable | Default | Notes |
|----------|---------|-------|
| `RAG_NANO_INDEX_DIR` | `./.rag-nano` | SQLite + vector matrix dir |
| `RAG_NANO_EMBEDDING_MODEL` | `intfloat/multilingual-e5-base` | sentence-transformers id |
| `RAG_NANO_EMBEDDING_BACKEND` | `local` | `local` or `mock` (tests only) |
| `RAG_NANO_HTTP_PORT` | `8089` | |
| `RAG_NANO_LOG_LEVEL` | `INFO` | |

## Operational notes

- **Hot-reload is not in v1.** After `ingest`, a running `serve` still holds the old in-memory matrix. Restart `serve` to pick up new content.
- **Atomic swap.** A request in flight reads the old matrix file; the next request opens the new one. The structured store and vector matrix stay mutually consistent at every observable moment.
- **What gets rejected on ingest.** Raw logs, oversized raw conversations, files with embedded credentials, unsupported file extensions. Each rejection is reported with a `RejectionReason` in the run report.
- **What `wipe-index --yes` does.** Deletes the entire `.rag-nano/` directory (SQLite + vectors). Eval history is untouched.
