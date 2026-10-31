from __future__ import annotations

from statistics import median

from .adjustments import floor_adjustment, size_adjustment
from .comparables import select_comparables
from .constants import MIN_COMPS
from .dto import CompRow, Confidence, Estimate, IndexPoint, Subject
from .price_index import time_factor


def _weight(distance_m: float, recency_days: float) -> float:
    dist = max(distance_m, 1.0)
    recency = max(recency_days, 1.0)
    return 1.0 / dist * 1.0 / recency


def _weighted_median(values: list[tuple[float, float]]) -> float:
    ordered = sorted(values, key=lambda item: item[0])
    total = sum(weight for _, weight in ordered)
    if total <= 0:
        return median(v for v, _ in ordered)
    running = 0.0
    for value, weight in ordered:
        running += weight
        if running >= total / 2.0:
            return value
    return ordered[-1][0]


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = pct * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def estimate_value(
    rows: list[CompRow],
    subject: Subject,
    *,
    index_points: list[IndexPoint],
) -> Estimate:
    selected = select_comparables(rows, subject)
    adjusted: list[tuple[float, float]] = []
    used_index = True
    for row in selected:
        if row.size_sqm is None or row.size_sqm <= 0:
            continue
        size = size_adjustment(subject_size_sqm=subject.size_sqm, comp_size_sqm=row.size_sqm)
        floor = floor_adjustment(subject_floor=subject.floor, comp_floor=row.floor)
        tf, ok = time_factor(index_points, as_of=subject.as_of, sale_at=row.effective_at)
        if not ok:
            used_index = False
        price = row.price_agorot * size.factor * floor.factor * tf
        recency = (subject.as_of - row.effective_at).total_seconds() / 86400.0
        adjusted.append((price, _weight(row.distance_m, recency)))
    if not adjusted:
        return Estimate(
            value_agorot=0,
            iqr_low_agorot=0,
            iqr_high_agorot=0,
            n_comps=0,
            confidence="thin",
        )
    prices = sorted(price for price, _ in adjusted)
    value = int(round(_weighted_median(adjusted)))
    low = int(round(_percentile(prices, 0.25)))
    high = int(round(_percentile(prices, 0.75)))
    confidence: Confidence
    if len(adjusted) < MIN_COMPS:
        confidence = "thin"
    elif not used_index:
        confidence = "limited_index"
    else:
        confidence = "ok"
    return Estimate(
        value_agorot=value,
        iqr_low_agorot=low,
        iqr_high_agorot=high,
        n_comps=len(adjusted),
        confidence=confidence,
    )
