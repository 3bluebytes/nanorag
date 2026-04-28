from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rag_nano.types import EvaluationRun


def append(run: EvaluationRun, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = _run_to_dict(run)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def previous_run(path: Path) -> EvaluationRun | None:
    if not path.exists():
        return None
    last_line: str | None = None
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if last_line is None:
        return None
    return _dict_to_run(json.loads(last_line))


def compare(current: EvaluationRun, previous: EvaluationRun | None) -> dict | None:
    if previous is None:
        return None
    return {
        "previous_run_id": previous.run_id,
        "recall_delta": current.metric_recall_at_k - previous.metric_recall_at_k,
        "hit_rate_delta": current.metric_hit_rate - previous.metric_hit_rate,
    }


def _run_to_dict(run: EvaluationRun) -> dict:
    return {
        "run_id": run.run_id,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat(),
        "case_count": run.case_count,
        "metric_recall_at_k": run.metric_recall_at_k,
        "metric_hit_rate": run.metric_hit_rate,
        "k": run.k,
        "embedding_model": run.embedding_model,
        "index_chunk_count": run.index_chunk_count,
        "git_sha": run.git_sha,
        "per_case_outcome": run.per_case_outcome,
        "delta_vs_previous": run.delta_vs_previous,
    }


def _dict_to_run(d: dict) -> EvaluationRun:
    return EvaluationRun(
        run_id=d["run_id"],
        started_at=datetime.fromisoformat(d["started_at"]),
        finished_at=datetime.fromisoformat(d["finished_at"]),
        case_count=d["case_count"],
        metric_recall_at_k=d["metric_recall_at_k"],
        metric_hit_rate=d["metric_hit_rate"],
        k=d["k"],
        embedding_model=d["embedding_model"],
        index_chunk_count=d["index_chunk_count"],
        per_case_outcome=d.get("per_case_outcome", []),
        delta_vs_previous=d.get("delta_vs_previous"),
        git_sha=d.get("git_sha"),
    )
