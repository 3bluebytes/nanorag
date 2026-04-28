#!/usr/bin/env bash
# Populate the local index with the bundled test fixture corpus so retrieval
# has something to return out of the box.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[rag-nano] Seeding dev corpus..."
uv run rag-nano wipe-index --yes 2>/dev/null || true
uv run rag-nano ingest tests/fixtures/seed_corpus/
echo "[rag-nano] Done."
