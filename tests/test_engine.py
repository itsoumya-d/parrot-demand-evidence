import math

import pytest

from parrot_demand.engine import (
    Evidence,
    Signal,
    TitleRecord,
    assess,
    clamp,
    confidence,
    cosine,
    jaccard,
    mean,
    momentum,
    population_std,
    rank,
    tf,
    tokens,
)


def record(title="The Last Signal", values=(10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21), evidence=True, audience=("a", "b", "c")):
    ev = [Evidence("https://source.example/a", "Audience demand accelerated across search and streaming signals in this market.", "search")] if evidence else []
    return TitleRecord(title, "NZ", [Signal("search", values, "https://source.example/a", 1.0)], ev, audience)


def test_tokens_lowercases_and_splits():
    assert tokens("Demand UP 24%") == ["demand", "up", "24"]


def test_tf_normalises():
    assert tf("a a b") == {"a": 2 / 3, "b": 1 / 3}


def test_mean_empty():
    assert mean([]) == 0


def test_mean_values():
    assert mean([1, 2, 3]) == 2


def test_population_std():
    assert population_std([2, 4, 4, 4, 5, 5, 7, 9]) == 2


def test_population_std_empty():
    assert population_std([]) == 0


def test_clamp():
    assert clamp(1.4) == 1 and clamp(-1) == 0


def test_momentum_positive():
    assert momentum([20, 20], [10, 10]) == 1


def test_momentum_zero_baseline():
    assert momentum([10], [0, 0]) == 0


def test_momentum_negative():
    assert momentum([5], [10]) == -0.5


def test_confidence_high_with_history():
    assert confidence([10, 11, 12, 13, 14, 15]) > 0.7


def test_confidence_low_with_one_value():
    assert confidence([10]) < 0.6


def test_cosine_identical():
    assert cosine({"a": 1, "b": 1}, {"a": 1, "b": 1}) == pytest.approx(1)


def test_cosine_disjoint():
    assert cosine({"a": 1}, {"b": 1}) == 0


def test_jaccard_overlap():
    assert jaccard(["a", "b"], ["b", "c"]) == 1 / 3


def test_jaccard_empty():
    assert jaccard([], []) == 0


def test_assess_strong_status():
    assert assess(record()).status == "strong"


def test_assess_unsupported_without_signals():
    result = assess(TitleRecord("T", "NZ", [], [], ()))
    assert result.status == "unsupported"
    assert "no_signals" in result.flags


def test_assess_unsupported_without_evidence():
    result = assess(record(evidence=False))
    assert "no_supported_evidence" in result.flags


def test_assess_conflicting_signals():
    item = TitleRecord("T", "NZ", [
        Signal("search", [10, 10, 10, 20], "https://a", 1),
        Signal("social", [20, 20, 10, 10], "https://b", 1),
    ], [Evidence("https://a", "Demand evidence for T", "search")])
    assert "conflicting_signals" in assess(item).flags


def test_assess_single_source_flag():
    assert "single_source" in assess(record()).flags


def test_assess_sparse_flag():
    item = record(values=(10, 11))
    assert any(flag.startswith("short_history") for flag in assess(item).flags)


def test_assess_drivers_sorted():
    result = assess(record())
    assert len(result.drivers) == 1


def test_assess_overlap():
    result = assess(record(), [record(), record("Other", audience=("b", "c", "d"))])
    assert 0 < result.overlap["Other"] < 1


def test_assess_explanation_mentions_confidence():
    assert "confidence" in assess(record()).explanation.lower()


def test_assess_empty_evidence_explanation():
    assert "no supporting citation" in assess(record(evidence=False)).explanation


def test_rank_orders_by_momentum():
    down = record("Down", values=tuple(reversed(range(1, 13))))
    up = record("Up")
    assert rank([down, up])[0].title == "Up"


def test_rank_returns_all():
    assert len(rank([record("A"), record("B")])) == 2


def test_assess_market_preserved():
    assert assess(record()).market == "NZ"


def test_assess_confidence_between_zero_and_one():
    value = assess(record()).confidence
    assert 0 <= value <= 1


def test_assess_negative_momentum():
    item = record(values=(30, 30, 30, 10, 10, 10))
    assert assess(item).momentum < 0
