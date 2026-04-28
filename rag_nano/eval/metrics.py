from __future__ import annotations


def recall_at_k(actual: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 1.0
    if k <= 0 or not actual:
        return 0.0
    top_k = set(actual[:k])
    matches = sum(1 for e in expected if e in top_k)
    return matches / len(expected)


def hit_rate(actual: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    if not actual:
        return 0.0
    actual_set = set(actual)
    for e in expected:
        if e in actual_set:
            return 1.0
    return 0.0
