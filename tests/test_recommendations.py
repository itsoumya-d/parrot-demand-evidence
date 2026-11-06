from datetime import date

import pytest

from parrot_demand.recommendations import (
    Candidate,
    ListeningEvent,
    Track,
    affinity,
    dcg,
    evaluate_ranking,
    freshness,
    ndcg_at_k,
    rank_candidates,
    recency_weight,
    repetition_penalty,
    score_candidate,
)

TODAY = date(2026, 11, 6)
TRACK = Track("t1", "a1", frozenset({"pop"}), date(2026, 10, 1))


def test_recency_decays_by_half_life():
    assert recency_weight(14, 14) == pytest.approx(0.5)


def test_recency_rejects_negative():
    with pytest.raises(ValueError):
        recency_weight(-1)


def test_recency_rejects_zero_half_life():
    with pytest.raises(ValueError):
        recency_weight(1, 0)


def test_affinity_is_zero_without_events():
    assert affinity([]) == 0.0


def test_affinity_rewards_recent_completion():
    recent = affinity([ListeningEvent("t1", 1, True)])
    old = affinity([ListeningEvent("t1", 60, True)])
    assert recent > old


def test_affinity_partial_completion_weighs_less():
    assert affinity([ListeningEvent("t1", 1, False)]) < affinity([ListeningEvent("t1", 1, True)])


def test_freshness_new_track_is_one():
    assert freshness(TODAY, TODAY) == 1.0


def test_freshness_old_track_is_zero():
    assert freshness(date(2026, 1, 1), TODAY) == 0.0


def test_freshness_future_release_is_zero():
    assert freshness(date(2026, 12, 1), TODAY) == 0.0


def test_repetition_penalty():
    assert repetition_penalty(3, 6) == 0.5


def test_repetition_penalty_caps_at_one():
    assert repetition_penalty(100) == 1.0


def test_score_is_bounded():
    candidate = Candidate(TRACK, 1, 1, 1, 0)
    assert 0 <= score_candidate(candidate) <= 1


def test_score_rejects_bad_weights():
    with pytest.raises(ValueError):
        score_candidate(Candidate(TRACK, 1, 1, 1, 0), (1, 1, 1, 1))


def test_rank_candidates_orders_by_score_and_id():
    a = Candidate(Track("a", "x", frozenset(), TODAY), 1, 0, 0, 0)
    b = Candidate(Track("b", "x", frozenset(), TODAY), 0.5, 0, 0, 0)
    ranked = rank_candidates([b, a])
    assert [item.track_id for item in ranked] == ["a", "b"]


def test_rank_candidates_rejects_zero_limit():
    with pytest.raises(ValueError):
        rank_candidates([], 0)


def test_rank_candidates_includes_reasons():
    ranked = rank_candidates([Candidate(TRACK, 1, 1, 1, 0)])
    assert "artist_affinity" in ranked[0].reasons


def test_dcg_prefers_higher_relevance():
    assert dcg([3, 0]) > dcg([0, 3])


def test_ndcg_perfect_ranking_is_one():
    assert ndcg_at_k(["a", "b"], {"a": 2, "b": 1}, 2) == 1.0


def test_ndcg_zero_without_relevance():
    assert ndcg_at_k(["a"], {"b": 1}, 1) == 0.0


def test_ndcg_rejects_zero_k():
    with pytest.raises(ValueError):
        ndcg_at_k(["a"], {"a": 1}, 0)


def test_evaluate_ranking_metrics():
    result = evaluate_ranking(["a", "b", "c"], {"a": 1, "c": 1}, 3)
    assert result["precision_at_k"] == pytest.approx(2 / 3)
    assert 0 < result["ndcg_at_k"] <= 1
