from rag_nano.eval.metrics import hit_rate, recall_at_k


class TestRecallAtK:
    def test_perfect_recall_is_one(self) -> None:
        assert recall_at_k(["a", "b", "c"], ["a", "b"], k=3) == 1.0

    def test_total_miss_is_zero(self) -> None:
        assert recall_at_k(["x", "y", "z"], ["a", "b"], k=3) == 0.0

    def test_partial_recall(self) -> None:
        assert recall_at_k(["a", "x", "y"], ["a", "b"], k=3) == 0.5

    def test_top_k_truncates(self) -> None:
        # 'b' is at position 4 (>= k); only 'a' counts.
        assert recall_at_k(["a", "x", "y", "z", "b"], ["a", "b"], k=3) == 0.5

    def test_empty_expected_is_vacuously_one(self) -> None:
        assert recall_at_k(["a"], [], k=3) == 1.0
        assert recall_at_k([], [], k=3) == 1.0

    def test_empty_actual_with_expected_is_zero(self) -> None:
        assert recall_at_k([], ["a"], k=3) == 0.0

    def test_zero_k_is_zero(self) -> None:
        assert recall_at_k(["a"], ["a"], k=0) == 0.0


class TestHitRate:
    def test_any_hit_is_one(self) -> None:
        assert hit_rate(["a", "x"], ["a", "b"]) == 1.0

    def test_no_hit_is_zero(self) -> None:
        assert hit_rate(["x", "y"], ["a", "b"]) == 0.0

    def test_empty_expected_is_one(self) -> None:
        assert hit_rate(["a"], []) == 1.0

    def test_empty_actual_with_expected_is_zero(self) -> None:
        assert hit_rate([], ["a"]) == 0.0
