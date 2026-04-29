from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml
from ulid import ULID

from rag_nano.config import Settings
from rag_nano.core.retrieval import Components, retrieve
from rag_nano.eval.history import append, compare, previous_run
from rag_nano.eval.metrics import recall_at_k
from rag_nano.types import (
    DataType,
    EvaluationCase,
    EvaluationRun,
    RetrievalFilters,
    RetrievalQuery,
)

logger = logging.getLogger(__name__)


def load_cases(path: Path) -> list[EvaluationCase]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    raw_cases = data.get("cases", []) if isinstance(data, dict) else (data or [])
    cases: list[EvaluationCase] = []
    for entry in raw_cases:
        cases.append(
            EvaluationCase(
                case_id=entry["case_id"],
                query=entry["query"],
                query_lang=entry["query_lang"],
                expected_data_type=DataType(entry["expected_data_type"]),
                mode=entry["mode"],
                expected_chunk_ids=list(entry.get("expected_chunk_ids") or []),
                expected_substring=entry.get("expected_substring") or "",
                notes=entry.get("notes") or "",
            )
        )
    return cases


def validate_composition(cases: list[EvaluationCase], corpus_data_types: set[str]) -> None:
    if len(cases) < 20:
        raise ValueError(f"Eval requires ≥20 cases; got {len(cases)}")
    case_data_types = {c.expected_data_type.value for c in cases}
    missing = corpus_data_types - case_data_types
    if missing:
        raise ValueError(f"Corpus contains data_types {sorted(missing)} with no matching eval case")
    langs = {c.query_lang for c in cases}
    if "zh" not in langs:
        raise ValueError("Eval requires ≥1 zh case")
    if "en" not in langs:
        raise ValueError("Eval requires ≥1 en case")


def evaluate_case(case: EvaluationCase, components: Components, k: int) -> dict:
    try:
        response = retrieve(
            RetrievalQuery(
                query=case.query,
                k=k,
                filters=RetrievalFilters(),
                debug=False,
            ),
            components,
        )
    except Exception as e:
        logger.warning(
            "Case retrieve failed",
            extra={"case_id": case.case_id, "error": str(e)},
        )
        return {
            "case_id": case.case_id,
            "hit": False,
            "recall_at_k": 0.0,
            "expected_rank": -1,
            "top_k_returned": [],
            "error": str(e),
        }

    returned_ids = [r.chunk_id for r in response.results]
    returned_texts = [r.text for r in response.results]

    if case.mode == "chunk_ids":
        recall = recall_at_k(returned_ids, case.expected_chunk_ids, k)
        hit = recall > 0.0
        expected_rank = -1
        expected_set = set(case.expected_chunk_ids)
        for i, cid in enumerate(returned_ids[:k]):
            if cid in expected_set:
                expected_rank = i
                break
    elif case.mode == "substring":
        substring_hit = any(case.expected_substring in t for t in returned_texts[:k])
        recall = 1.0 if substring_hit else 0.0
        hit = substring_hit
        expected_rank = -1
        for i, t in enumerate(returned_texts[:k]):
            if case.expected_substring in t:
                expected_rank = i
                break
    else:
        return {
            "case_id": case.case_id,
            "hit": False,
            "recall_at_k": 0.0,
            "expected_rank": -1,
            "top_k_returned": returned_ids[:k],
            "error": f"unknown mode: {case.mode}",
        }

    return {
        "case_id": case.case_id,
        "hit": hit,
        "recall_at_k": recall,
        "expected_rank": expected_rank,
        "top_k_returned": returned_ids[:k],
        "error": None,
    }


def run_eval(
    cases_path: Path,
    history_path: Path,
    components: Components,
    settings: Settings,
    k: int = 5,
) -> EvaluationRun:
    started_at = datetime.now(UTC)
    cases = load_cases(cases_path)

    corpus_stats = components.structured_store.get_stats()
    corpus_data_types = set(corpus_stats.get("by_data_type", {}).keys())
    validate_composition(cases, corpus_data_types)

    per_case_outcome: list[dict] = []
    recall_total = 0.0
    hit_total = 0.0
    for case in cases:
        outcome = evaluate_case(case, components, k)
        per_case_outcome.append(outcome)
        recall_total += outcome["recall_at_k"]
        hit_total += 1.0 if outcome["hit"] else 0.0

    case_count = len(cases)
    metric_recall = recall_total / case_count if case_count else 0.0
    metric_hit = hit_total / case_count if case_count else 0.0
    finished_at = datetime.now(UTC)

    prev = previous_run(history_path)
    run = EvaluationRun(
        run_id=str(ULID()),
        started_at=started_at,
        finished_at=finished_at,
        case_count=case_count,
        metric_recall_at_k=metric_recall,
        metric_hit_rate=metric_hit,
        k=k,
        embedding_model=settings.embedding_model,
        index_chunk_count=corpus_stats.get("chunk_count", 0),
        per_case_outcome=per_case_outcome,
        delta_vs_previous=None,
        git_sha=_detect_git_sha(),
    )
    run.delta_vs_previous = compare(run, prev)
    append(run, history_path)
    return run


def _detect_git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if len(sha) == 40:
                return sha
    except Exception:
        return None
    return None
