from datetime import datetime, timezone
from pathlib import Path

from rag_nano.eval.history import append, compare, previous_run
from rag_nano.types import EvaluationRun


def _make_run(run_id: str, recall: float, hit: float) -> EvaluationRun:
    now = datetime.now(timezone.utc)
    return EvaluationRun(
        run_id=run_id,
        started_at=now,
        finished_at=now,
        case_count=20,
        metric_recall_at_k=recall,
        metric_hit_rate=hit,
        k=5,
        embedding_model="mock",
        index_chunk_count=42,
        per_case_outcome=[{"case_id": "c1", "hit": True, "recall_at_k": 1.0}],
        delta_vs_previous=None,
        git_sha=None,
    )


class TestAppend:
    def test_append_writes_single_jsonl_line(self, tmp_path: Path) -> None:
        history = tmp_path / "history.jsonl"
        append(_make_run("run-1", 0.5, 0.6), history)
        content = history.read_text(encoding="utf-8")
        assert content.count("\n") == 1
        assert content.endswith("\n")

    def test_append_appends_not_overwrites(self, tmp_path: Path) -> None:
        history = tmp_path / "history.jsonl"
        append(_make_run("run-1", 0.5, 0.6), history)
        append(_make_run("run-2", 0.7, 0.8), history)
        lines = history.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_append_creates_parent_dir(self, tmp_path: Path) -> None:
        history = tmp_path / "nested" / "history.jsonl"
        append(_make_run("run-1", 0.5, 0.6), history)
        assert history.exists()


class TestPreviousRun:
    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert previous_run(tmp_path / "nope.jsonl") is None

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        history = tmp_path / "history.jsonl"
        history.write_text("", encoding="utf-8")
        assert previous_run(history) is None

    def test_returns_most_recent_record(self, tmp_path: Path) -> None:
        history = tmp_path / "history.jsonl"
        append(_make_run("run-1", 0.5, 0.6), history)
        append(_make_run("run-2", 0.7, 0.8), history)
        prev = previous_run(history)
        assert prev is not None
        assert prev.run_id == "run-2"
        assert prev.metric_recall_at_k == 0.7


class TestCompare:
    def test_returns_none_when_previous_is_none(self) -> None:
        current = _make_run("run-1", 0.5, 0.6)
        assert compare(current, None) is None

    def test_computes_deltas(self) -> None:
        prev = _make_run("run-1", 0.5, 0.6)
        current = _make_run("run-2", 0.7, 0.55)
        delta = compare(current, prev)
        assert delta is not None
        assert delta["previous_run_id"] == "run-1"
        assert delta["recall_delta"] == 0.7 - 0.5
        assert abs(delta["hit_rate_delta"] - (0.55 - 0.6)) < 1e-9

    def test_round_trip_via_jsonl(self, tmp_path: Path) -> None:
        history = tmp_path / "history.jsonl"
        original = _make_run("run-1", 0.5, 0.6)
        append(original, history)
        loaded = previous_run(history)
        assert loaded is not None
        assert loaded.run_id == original.run_id
        assert loaded.metric_recall_at_k == original.metric_recall_at_k
        assert loaded.metric_hit_rate == original.metric_hit_rate
        assert loaded.case_count == original.case_count
