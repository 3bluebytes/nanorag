import pytest

from rag_nano.eval.runner import validate_composition
from rag_nano.types import DataType, EvaluationCase


def _case(case_id: str, lang: str, dt: DataType) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        query="q",
        query_lang=lang,
        expected_data_type=dt,
        mode="substring",
        expected_substring="x",
    )


def _build_cases(zh: int, en: int, dt: DataType = DataType.faq) -> list[EvaluationCase]:
    cases = [_case(f"zh-{i}", "zh", dt) for i in range(zh)]
    cases += [_case(f"en-{i}", "en", dt) for i in range(en)]
    return cases


class TestValidateComposition:
    def test_passes_with_valid_composition(self) -> None:
        cases = _build_cases(zh=10, en=10, dt=DataType.faq)
        validate_composition(cases, corpus_data_types={"faq"})

    def test_rejects_under_twenty_cases(self) -> None:
        cases = _build_cases(zh=5, en=5)
        with pytest.raises(ValueError, match="≥20 cases"):
            validate_composition(cases, corpus_data_types={"faq"})

    def test_rejects_missing_corpus_data_type(self) -> None:
        cases = _build_cases(zh=10, en=10, dt=DataType.faq)
        with pytest.raises(ValueError, match="sop"):
            validate_composition(cases, corpus_data_types={"faq", "sop"})

    def test_rejects_missing_zh(self) -> None:
        cases = _build_cases(zh=0, en=20)
        with pytest.raises(ValueError, match="zh"):
            validate_composition(cases, corpus_data_types={"faq"})

    def test_rejects_missing_en(self) -> None:
        cases = _build_cases(zh=20, en=0)
        with pytest.raises(ValueError, match="en"):
            validate_composition(cases, corpus_data_types={"faq"})

    def test_passes_when_corpus_is_empty(self) -> None:
        # An empty corpus drops the per-data-type rule.
        cases = _build_cases(zh=10, en=10)
        validate_composition(cases, corpus_data_types=set())

    def test_passes_with_multiple_data_types_covered(self) -> None:
        cases = (
            [_case(f"zh-{i}", "zh", DataType.faq) for i in range(5)]
            + [_case(f"zh-sop-{i}", "zh", DataType.sop) for i in range(5)]
            + [_case(f"en-wiki-{i}", "en", DataType.wiki) for i in range(5)]
            + [_case(f"en-code-{i}", "en", DataType.code_summary) for i in range(5)]
        )
        validate_composition(
            cases,
            corpus_data_types={"faq", "sop", "wiki", "code_summary"},
        )
