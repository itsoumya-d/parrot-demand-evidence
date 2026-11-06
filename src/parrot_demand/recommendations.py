from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from .engine import clamp


@dataclass(frozen=True)
class Track:
    track_id: str
    artist_id: str
    genres: frozenset[str]
    release_date: date


@dataclass(frozen=True)
class ListeningEvent:
    track_id: str
    days_ago: int
    completed: bool = True


@dataclass(frozen=True)
class Candidate:
    track: Track
    affinity: float
    co_listen: float
    freshness: float
    repetition: float


@dataclass(frozen=True)
class RankedTrack:
    track_id: str
    score: float
    reasons: tuple[str, ...]


def recency_weight(days_ago: int, half_life_days: int = 14) -> float:
    if days_ago < 0:
        raise ValueError("days_ago cannot be negative")
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    return 0.5 ** (days_ago / half_life_days)


def affinity(events: Sequence[ListeningEvent], half_life_days: int = 14) -> float:
    if not events:
        return 0.0
    total = sum(recency_weight(event.days_ago, half_life_days) * (1.0 if event.completed else 0.35) for event in events)
    return clamp(total / max(1, len(events)))


def freshness(release_date: date, today: date, horizon_days: int = 90) -> float:
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    age = (today - release_date).days
    if age < 0:
        return 0.0
    return clamp(1.0 - age / horizon_days)


def repetition_penalty(plays_last_7d: int, cap: int = 5) -> float:
    if plays_last_7d < 0:
        raise ValueError("plays cannot be negative")
    return clamp(plays_last_7d / cap)


def score_candidate(candidate: Candidate, weights: tuple[float, float, float, float] = (0.45, 0.25, 0.20, 0.10)) -> float:
    w_affinity, w_co_listen, w_freshness, w_repetition = weights
    if abs(sum(weights) - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1")
    raw = (
        w_affinity * clamp(candidate.affinity)
        + w_co_listen * clamp(candidate.co_listen)
        + w_freshness * clamp(candidate.freshness)
        - w_repetition * clamp(candidate.repetition)
    )
    return round(clamp(raw), 6)


def rank_candidates(candidates: Iterable[Candidate], limit: int = 10, weights: tuple[float, float, float, float] = (0.45, 0.25, 0.20, 0.10)) -> list[RankedTrack]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    ranked = []
    for candidate in candidates:
        score = score_candidate(candidate, weights)
        reasons = []
        if candidate.affinity > 0:
            reasons.append("artist_affinity")
        if candidate.co_listen > 0:
            reasons.append("co_listen")
        if candidate.freshness > 0:
            reasons.append("fresh_release")
        if candidate.repetition > 0:
            reasons.append("repetition_penalty")
        ranked.append(RankedTrack(candidate.track.track_id, score, tuple(reasons)))
    return sorted(ranked, key=lambda item: (-item.score, item.track_id))[:limit]


def dcg(relevances: Sequence[float]) -> float:
    return sum((2**rel - 1) / math.log2(index + 2) for index, rel in enumerate(relevances))


def ndcg_at_k(ranked: Sequence[str], relevance: dict[str, float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    gains = [relevance.get(track_id, 0.0) for track_id in ranked[:k]]
    ideal = sorted(relevance.values(), reverse=True)[:k]
    denominator = dcg(ideal)
    return 0.0 if denominator == 0 else round(dcg(gains) / denominator, 6)


def evaluate_ranking(ranked: Sequence[str], relevance: dict[str, float], k: int = 10) -> dict[str, float]:
    return {
        "ndcg_at_k": ndcg_at_k(ranked, relevance, k),
        "precision_at_k": round(sum(1 for track_id in ranked[:k] if relevance.get(track_id, 0) > 0) / k, 6),
    }
