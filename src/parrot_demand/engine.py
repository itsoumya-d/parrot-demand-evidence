from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Mapping, Sequence

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def population_std(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def momentum(recent: Sequence[float], baseline: Sequence[float]) -> float:
    base = mean(baseline)
    if base <= 0:
        return 0.0
    return (mean(recent) - base) / base


def confidence(values: Sequence[float], minimum: int = 4) -> float:
    if not values:
        return 0.0
    coverage = clamp(len(values) / minimum)
    variation = population_std(values) / (mean(values) or 1.0)
    return round(clamp(0.35 + 0.55 * coverage - 0.25 * min(variation, 1.0), 0.05, 0.98), 4)


def cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    dot = sum(left.get(key, 0.0) * right.get(key, 0.0) for key in keys)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def tf(text: str) -> dict[str, float]:
    counts = Counter(tokens(text))
    total = sum(counts.values()) or 1
    return {token: count / total for token, count in counts.items()}


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass(frozen=True)
class Signal:
    kind: str
    values: Sequence[float]
    source: str
    weight: float = 1.0


@dataclass(frozen=True)
class Evidence:
    source: str
    quote: str
    kind: str


@dataclass(frozen=True)
class TitleRecord:
    title: str
    market: str
    signals: Sequence[Signal]
    evidence: Sequence[Evidence]
    audience: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class Driver:
    kind: str
    value: float
    weight: float
    source: str


@dataclass(frozen=True)
class EvidenceMatch:
    source: str
    quote: str
    support: float


@dataclass(frozen=True)
class Assessment:
    title: str
    market: str
    momentum: float
    confidence: float
    status: str
    drivers: Sequence[Driver]
    evidence: Sequence[EvidenceMatch]
    overlap: Mapping[str, float]
    flags: Sequence[str]
    explanation: str


def assess(record: TitleRecord, corpus: Sequence[TitleRecord] | None = None) -> Assessment:
    if not record.signals:
        return Assessment(record.title, record.market, 0.0, 0.0, "unsupported", (), (), {}, ("no_signals",), "No demand signals were supplied.")
    contributions: list[Driver] = []
    all_values: list[float] = []
    flags: list[str] = []
    signal_momentum: list[float] = []
    for signal in record.signals:
        if len(signal.values) < 2:
            flags.append(f"sparse:{signal.kind}")
            continue
        split = max(1, len(signal.values) // 3)
        recent = signal.values[-split:]
        baseline = signal.values[:-split] or signal.values
        change = momentum(recent, baseline)
        signal_momentum.append(change)
        contributions.append(Driver(signal.kind, round(change, 4), signal.weight, signal.source))
        all_values.extend(signal.values)
        if len(signal.values) < 4:
            flags.append(f"short_history:{signal.kind}")
    weighted = sum(driver.value * driver.weight for driver in contributions)
    total_weight = sum(driver.weight for driver in contributions) or 1.0
    score = weighted / total_weight
    conf = confidence(all_values)
    if len({driver.source for driver in contributions}) == 1:
        flags.append("single_source")
    if any(value > 0 for value in signal_momentum) and any(value < 0 for value in signal_momentum):
        flags.append("conflicting_signals")
    evidence_matches = support_evidence(record, corpus or [])
    if not evidence_matches:
        flags.append("no_supported_evidence")
    if conf < 0.55:
        flags.append("low_confidence")
    if score > 0.08 and evidence_matches and conf >= 0.55:
        status = "strong"
    elif score > 0.02 or evidence_matches:
        status = "mixed"
    else:
        status = "unsupported"
    overlap = {}
    if corpus:
        for other in corpus:
            if other.title != record.title:
                overlap[other.title] = round(jaccard(record.audience, other.audience), 4)
    explanation = explain(record.title, score, conf, status, contributions, evidence_matches, flags)
    return Assessment(record.title, record.market, round(score, 4), conf, status,
                      tuple(sorted(contributions, key=lambda d: abs(d.value * d.weight), reverse=True)),
                      tuple(evidence_matches), overlap, tuple(sorted(set(flags))), explanation)


def support_evidence(record: TitleRecord, corpus: Sequence[TitleRecord]) -> list[EvidenceMatch]:
    claim = f"{record.title} demand momentum audience sentiment market"
    claim_tf = tf(claim)
    matches: list[EvidenceMatch] = []
    for evidence in record.evidence:
        score = cosine(claim_tf, tf(evidence.quote + " " + record.title))
        if score >= 0.08:
            matches.append(EvidenceMatch(evidence.source, evidence.quote, round(score, 4)))
    return sorted(matches, key=lambda item: item.support, reverse=True)[:3]


def explain(title: str, score: float, conf: float, status: str, drivers: Sequence[Driver], evidence: Sequence[EvidenceMatch], flags: Sequence[str]) -> str:
    direction = "up" if score > 0 else "down" if score < 0 else "flat"
    top = drivers[0].kind if drivers else "no signal"
    evidence_text = f"{len(evidence)} cited source(s)" if evidence else "no supporting citation"
    flag_text = ", ".join(flags) if flags else "no flags"
    return f"{title} momentum is {direction} ({score:+.1%}); lead driver: {top}; confidence {conf:.0%}; {evidence_text}; {flag_text}."


def rank(records: Sequence[TitleRecord]) -> list[Assessment]:
    return sorted((assess(record, records) for record in records), key=lambda item: item.momentum, reverse=True)
