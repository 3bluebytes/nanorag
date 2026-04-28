import json
from pathlib import Path

import pytest
import yaml

from rag_nano.components.embedding import MockEmbeddingProvider
from rag_nano.components.reranker import IdentityReranker
from rag_nano.components.retriever import CosineTopKRetriever
from rag_nano.config import Settings
from rag_nano.core.retrieval import Components
from rag_nano.eval.runner import run_eval


SEED_CASES_YAML = Path("eval/cases.yaml")


@pytest.fixture
def components(seed_index_via_ingest_fixture) -> Components:
    structured, vector = seed_index_via_ingest_fixture
    return Components(
        embedding_provider=MockEmbeddingProvider(),
        vector_store=vector,
        retriever=CosineTopKRetriever(),
        reranker=IdentityReranker(),
        structured_store=structured,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        embedding_backend="mock",
        vector_store="in_memory",
        structured_store="in_memory",
        reranker="identity",
    )


def _write_minimal_cases(path: Path, broken_chunk_id: str | None = None) -> None:
    cases: list[dict] = []
    # 10 zh + 10 en across the four corpus data types
    plan = [
        ("faq", "passage", 3, 2),
        ("sop", "灰度发布", 3, 2),
        ("wiki", "decoupled", 2, 3),
        ("code_summary", "chunk_markdown", 2, 3),
    ]
    for dt, substring, n_zh, n_en in plan:
        for i in range(n_zh):
            cases.append(
                {
                    "case_id": f"{dt}-zh-{i:03d}",
                    "query": f"查询 {dt} {i}",
                    "query_lang": "zh",
                    "expected_data_type": dt,
                    "mode": "substring",
                    "expected_substring": substring,
                }
            )
        for i in range(n_en):
            cases.append(
                {
                    "case_id": f"{dt}-en-{i:03d}",
                    "query": f"query {dt} {i}",
                    "query_lang": "en",
                    "expected_data_type": dt,
                    "mode": "substring",
                    "expected_substring": substring,
                }
            )
    if broken_chunk_id is not None:
        # Replace the last case with a broken chunk_ids case (FR-021).
        cases[-1] = {
            "case_id": "code_summary-broken",
            "query": "broken case",
            "query_lang": "en",
            "expected_data_type": "code_summary",
            "mode": "chunk_ids",
            "expected_chunk_ids": [broken_chunk_id],
        }
    path.write_text(yaml.safe_dump({"cases": cases}, allow_unicode=True), encoding="utf-8")


class TestEvalPipeline:
    def test_runs_in_one_command_and_emits_metric(
        self, tmp_path: Path, components: Components, settings: Settings
    ) -> None:
        cases_file = tmp_path / "cases.yaml"
        history_file = tmp_path / "history.jsonl"
        _write_minimal_cases(cases_file)

        run = run_eval(cases_file, history_file, components, settings, k=5)
        assert run.case_count == 20
        assert 0.0 <= run.metric_recall_at_k <= 1.0
        assert 0.0 <= run.metric_hit_rate <= 1.0
        assert history_file.exists()
        assert history_file.read_text(encoding="utf-8").strip().count("\n") == 0  # one line

    def test_consecutive_runs_surface_delta(
        self, tmp_path: Path, components: Components, settings: Settings
    ) -> None:
        cases_file = tmp_path / "cases.yaml"
        history_file = tmp_path / "history.jsonl"
        _write_minimal_cases(cases_file)

        first = run_eval(cases_file, history_file, components, settings, k=5)
        assert first.delta_vs_previous is None  # first run

        second = run_eval(cases_file, history_file, components, settings, k=5)
        assert second.delta_vs_previous is not None
        assert second.delta_vs_previous["previous_run_id"] == first.run_id
        # Same code, same corpus, same cases → deltas == 0.
        assert second.delta_vs_previous["recall_delta"] == 0.0
        assert second.delta_vs_previous["hit_rate_delta"] == 0.0

        # Two records persisted.
        lines = history_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_updating_cases_reflects_without_code_changes(
        self, tmp_path: Path, components: Components, settings: Settings
    ) -> None:
        cases_file = tmp_path / "cases.yaml"
        history_file = tmp_path / "history.jsonl"

        _write_minimal_cases(cases_file)
        first = run_eval(cases_file, history_file, components, settings, k=5)
        first_count = first.case_count

        # Add a 21st case → re-run picks it up without rebuilding the runner.
        existing = yaml.safe_load(cases_file.read_text(encoding="utf-8"))
        existing["cases"].append(
            {
                "case_id": "extra-en-001",
                "query": "extra",
                "query_lang": "en",
                "expected_data_type": "faq",
                "mode": "substring",
                "expected_substring": "passage",
            }
        )
        cases_file.write_text(
            yaml.safe_dump(existing, allow_unicode=True), encoding="utf-8"
        )

        second = run_eval(cases_file, history_file, components, settings, k=5)
        assert second.case_count == first_count + 1

    def test_broken_case_is_flagged_run_does_not_abort(
        self, tmp_path: Path, components: Components, settings: Settings
    ) -> None:
        cases_file = tmp_path / "cases.yaml"
        history_file = tmp_path / "history.jsonl"
        _write_minimal_cases(
            cases_file,
            broken_chunk_id="01PLACEHOLDER000000000000000000",
        )

        run = run_eval(cases_file, history_file, components, settings, k=5)
        assert run.case_count == 20

        broken = next(
            o for o in run.per_case_outcome if o["case_id"] == "code_summary-broken"
        )
        assert broken["hit"] is False
        assert broken["recall_at_k"] == 0.0
        assert broken["error"] is None  # not an exception — just a miss

        # History still appended despite the broken case.
        record = json.loads(history_file.read_text(encoding="utf-8").strip())
        assert record["case_count"] == 20
