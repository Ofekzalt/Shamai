from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import median

from .dto import CompRow, IndexPoint


def _month_start(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def build_index(
    rows: list[CompRow],
    *,
    as_of: datetime,
    statistical_area: str,
) -> list[IndexPoint]:
    buckets: dict[datetime, list[float]] = defaultdict(list)
    for row in rows:
        if row.available_at > as_of:
            continue
        if row.statistical_area != statistical_area:
            continue
        if row.size_sqm is None or row.size_sqm <= 0:
            continue
        month = _month_start(row.effective_at)
        if month > as_of:
            continue
        buckets[month].append(row.price_agorot / row.size_sqm)
    return [
        IndexPoint(period_end=month, nis_per_sqm=median(values), statistical_area=statistical_area)
        for month, values in sorted(buckets.items())
    ]


def _nearest_on_or_before(series: list[IndexPoint], when: datetime) -> IndexPoint | None:
    eligible = [p for p in series if p.period_end <= when]
    if not eligible:
        return None
    return eligible[-1]


def time_factor(
    series: list[IndexPoint],
    *,
    as_of: datetime,
    sale_at: datetime,
) -> tuple[float, bool]:
    if not series:
        return 1.0, False
    at_as_of = _nearest_on_or_before(series, as_of)
    at_sale = _nearest_on_or_before(series, sale_at)
    if at_as_of is None or at_sale is None or at_sale.nis_per_sqm == 0:
        return 1.0, False
    return at_as_of.nis_per_sqm / at_sale.nis_per_sqm, True
