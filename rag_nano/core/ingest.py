from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rag_nano.components.embedding import get_embedding_provider
from rag_nano.components.vector_store import get_vector_store
from rag_nano.config import Settings
from rag_nano.ingest.loaders import load_file
from rag_nano.ingest.runner import commit_source, run_pipeline
from rag_nano.types import DataType, IngestRunReport

logger = logging.getLogger(__name__)


def ingest(
    paths: list[Path],
    structured_store: Any,
    vector_store: Any,
    settings: Settings,
) -> IngestRunReport:
    embedding_provider = get_embedding_provider(settings)

    report = IngestRunReport()
    by_data_type: dict[str, int] = {}

    for path in paths:
        if path.is_dir():
            children = list(path.iterdir())
        else:
            children = [path]

        for child in children:
            if child.is_dir():
                continue

            loader_result = load_file(child)
            if loader_result.rejection_reason:
                report.rejected += 1
                report.per_item_reasons.append((str(child), loader_result.rejection_reason))
                logger.info("Rejected", extra={"path": str(child), "reason": loader_result.rejection_reason})
                continue

            item = loader_result.item
            result = run_pipeline(
                item,
                structured_store,
                settings,
                embedding_provider,
                vector_store,
            )

            if result.rejected:
                report.rejected += 1
                report.per_item_reasons.append((str(child), result.rejected))
                logger.info("Rejected", extra={"path": str(child), "reason": result.rejected})
                continue

            commit_source(result, structured_store, settings)
            report.accepted += 1
            report.total_chunks += len(result.chunks)

            dtype_key = result.source.data_type.value if result.source else "unknown"
            by_data_type[dtype_key] = by_data_type.get(dtype_key, 0) + len(result.chunks)
            report.per_item_reasons.append((str(child), None))
            logger.info("Ingested", extra={"path": str(child), "chunks": len(result.chunks)})

    report.by_data_type = by_data_type
    return report
