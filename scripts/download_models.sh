#!/usr/bin/env bash
# Pre-fetch embedding model weights so the first ingest/retrieval call is fast.
# One-shot; idempotent.
set -euo pipefail

MODEL="${RAG_NANO_EMBEDDING_MODEL:-intfloat/multilingual-e5-base}"

echo "[rag-nano] warming embedding model cache: ${MODEL}"
uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MODEL}')"
echo "[rag-nano] done."
