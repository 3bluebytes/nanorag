# Quickstart: rag-nano v1

**Feature**: 001-minimal-rag-loop · **Date**: 2026-04-28

This guide walks through bringing up the v1 librarian end-to-end on a local workstation, then shows two integration patterns (chat-style agent and workflow-style agent) to satisfy Constitution VIII's requirement for ≥2 documented integration examples.

---

## Prerequisites

- macOS 13+ / Linux / WSL2
- Python 3.11+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- ~3 GB free disk for the embedding model weights
- (Optional but recommended) a local git checkout of some real curated knowledge (FAQs, SOPs, wiki exports) to ingest

## First-time setup (5 commands)

```bash
# 1. Clone & enter the repo
cd /path/to/rag-nano

# 2. Create the project's virtualenv and install pinned deps
uv sync

# 3. Pre-fetch embedding model weights (~2.3 GB; first-run only)
uv run scripts/download_models.sh

# 4. (Optional) Seed a tiny dev corpus so retrieval has something to return
uv run scripts/seed_dev_corpus.sh

# 5. Start the HTTP server (default: http://127.0.0.1:8089)
uv run rag-nano serve
```

The server is ready when `curl http://127.0.0.1:8089/v1/health` returns `"status": "ok"`.

## Daily-use commands (Typer CLI)

```bash
uv run rag-nano ingest <path-or-glob> [--data-type faq|sop|wiki|...] [--category <label>]
uv run rag-nano serve [--host 127.0.0.1] [--port 8089]
uv run rag-nano eval [--k 5] [--out -]
uv run rag-nano stats
uv run rag-nano wipe-index --yes              # destructive; prompts unless --yes
```

`rag-nano ingest` runs end-to-end: load → value-gate → credential-scan → chunk → embed → atomic commit (SQLite + vector matrix). The terminal prints a per-source line and a final summary (accepted, rejected with reason, total chunks). Re-ingesting the same `--source-path` with new content replaces previous chunks atomically.

`rag-nano eval` runs every case in `eval/cases.yaml`, computes recall@k and hit_rate, appends the result to `eval/history.jsonl`, and prints the metric and its delta vs. the previous run. Exit code is 0 always (per FR-021 a single bad case must not fail the run); use `--fail-on-regression` to flip the exit code on a recall_delta < 0.

## Configuration (environment variables / `.env`)

| Variable | Default | Notes |
|----------|---------|-------|
| `RAG_NANO_INDEX_DIR` | `./.rag-nano` | Where SQLite + vector matrix live. |
| `RAG_NANO_EMBEDDING_MODEL` | `intfloat/multilingual-e5-base` | Any sentence-transformers-compatible model id. |
| `RAG_NANO_EMBEDDING_BACKEND` | `local` | `local` or `mock` (test only). Future: `hosted`. |
| `RAG_NANO_VECTOR_STORE` | `numpy_flat` | `numpy_flat` or `in_memory`. |
| `RAG_NANO_STRUCTURED_STORE` | `sqlite` | `sqlite` or `in_memory`. |
| `RAG_NANO_RERANKER` | `identity` | `identity` only in v1. |
| `RAG_NANO_LOG_LEVEL` | `INFO` | Standard Python logging level. |
| `RAG_NANO_HTTP_HOST` / `RAG_NANO_HTTP_PORT` | `127.0.0.1` / `8089` | |

Copy `.env.example` to `.env` to override.

---

## Integration example A — chat-style agent (Constitution VIII proof point #1)

A conversational front-desk agent decides that short-term memory cannot satisfy the user's question and dispatches a query to the librarian:

```python
# A minimal sketch — your agent stays in your repo; this is the librarian-side touchpoint only.
import httpx

LIBRARIAN_URL = "http://127.0.0.1:8089/v1/retrieve"

def ask_librarian(user_question: str, k: int = 5) -> list[dict]:
    """Return up to k attributed knowledge chunks for the question.

    The agent owns prompt construction, dialogue context, and answer generation.
    The librarian only returns chunks + provenance.
    """
    resp = httpx.post(
        LIBRARIAN_URL,
        json={"query": user_question, "k": k},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()["results"]

def render_for_chat(results: list[dict]) -> str:
    """The agent decides how to present the chunks; the librarian does not."""
    if not results:
        return "I don't have anything authoritative to cite on that."
    bullets = []
    for r in results:
        bullets.append(
            f"- {r['text'][:240]}…\n  source: {r['source_path']} ({r['data_type']}, score {r['score']:.2f})"
        )
    return "Here's what the knowledge base has, with sources:\n" + "\n".join(bullets)
```

Notice what is **not** in the librarian: no system prompt, no role tags, no markdown rendering rules, no chat-history context handling. Those belong to the agent — the librarian stays neutral.

---

## Integration example B — workflow-style agent (Constitution VIII proof point #2)

A non-conversational batch workflow (e.g. a nightly report generator) needs to look up authoritative documentation for every issue in a list:

```python
import httpx
import json
import sys

LIBRARIAN_URL = "http://127.0.0.1:8089/v1/retrieve"

def lookup_for_issue(issue_title: str) -> dict:
    """For each issue, return the top SOP and FAQ chunks attributed by source."""
    resp = httpx.post(
        LIBRARIAN_URL,
        json={
            "query": issue_title,
            "k": 3,
            "filters": {"data_types": ["sop", "faq"]},
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()

def main(issues_path: str) -> None:
    with open(issues_path) as f:
        for line in f:
            issue = json.loads(line)
            res = lookup_for_issue(issue["title"])
            issue["librarian_top_k"] = [
                {
                    "source_path": r["source_path"],
                    "score": r["score"],
                    "data_type": r["data_type"],
                    "preview": r["text"][:160],
                }
                for r in res["results"]
            ]
            print(json.dumps(issue, ensure_ascii=False))

if __name__ == "__main__":
    main(sys.argv[1])
```

This integration uses the same HTTP contract, no client SDK required, and again contains zero librarian-specific business logic on the librarian side. The workflow filters by `data_types` to bias toward SOPs and FAQs — that policy lives in the agent, not in the librarian.

---

## What "v1 done" looks like

You can run the following end-to-end and have it succeed cleanly:

```bash
uv run rag-nano wipe-index --yes
uv run rag-nano ingest tests/fixtures/seed_corpus/
uv run rag-nano stats                    # confirms ≥1 source, ≥1 chunk per data type
uv run rag-nano serve &                  # background it
sleep 2
curl -s http://127.0.0.1:8089/v1/health  # status: ok
curl -s -X POST http://127.0.0.1:8089/v1/retrieve \
     -H 'content-type: application/json' \
     -d '{"query":"什么是冷数据？","k":3}'   # returns 3 attributed results
curl -s -X POST http://127.0.0.1:8089/v1/retrieve \
     -H 'content-type: application/json' \
     -d '{"query":"deploy hotfix steps","k":3,"filters":{"data_types":["sop"]}}'   # returns 3 attributed SOPs
uv run rag-nano eval                      # prints recall@5, writes a record to eval/history.jsonl
pytest                                    # all unit + integration + contract + swappability tests pass
kill %1
```

Once that script runs green twice in a row (proving reproducibility per SC-007), v1 is shippable.
