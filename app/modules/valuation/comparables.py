from __future__ import annotations

from datetime import timedelta

from .constants import MIN_COMPS, RADIUS_M, SIZE_TOLERANCE, TIME_DAYS, WIDEN_ORDER
from .dto import CompRow, Subject


def _usable(row: CompRow, subject: Subject) -> bool:
    if row.available_at > subject.as_of:
        return False
    if subject.source_row_id is not None and row.source_row_id == subject.source_row_id:
        return False
    if row.price_agorot <= 0 or row.size_sqm is None or row.size_sqm <= 0:
        return False
    return True


def _within(
    row: CompRow,
    subject: Subject,
    *,
    radius_m: float,
    time_days: int,
    size_tol: float,
) -> bool:
    if row.distance_m > radius_m:
        return False
    if (subject.as_of - row.effective_at) > timedelta(days=time_days):
        return False
    if row.effective_at > subject.as_of:
        return False
    size = row.size_sqm
    if size is None:
        return False
    lo = subject.size_sqm * (1.0 - size_tol)
    hi = subject.size_sqm * (1.0 + size_tol)
    return lo <= size <= hi


def select_comparables(
    rows: list[CompRow],
    subject: Subject,
    *,
    widen: bool = True,
    radius_m: float | None = None,
) -> list[CompRow]:
    pool = [row for row in rows if _usable(row, subject)]
    radius_i = 0
    time_i = 0
    size_i = 0
    start_radius = radius_m if radius_m is not None else RADIUS_M[0]

    def _selected(*, rad: float, time_days: int, size_tol: float) -> list[CompRow]:
        return [
            row
            for row in pool
            if _within(
                row,
                subject,
                radius_m=rad,
                time_days=time_days,
                size_tol=size_tol,
            )
        ]

    selected = _selected(
        rad=start_radius,
        time_days=TIME_DAYS[time_i],
        size_tol=SIZE_TOLERANCE[size_i],
    )
    if not widen:
        return selected
    for dim in WIDEN_ORDER:
        while len(selected) < MIN_COMPS:
            if dim == "radius" and radius_i < len(RADIUS_M) - 1:
                radius_i += 1
            elif dim == "time" and time_i < len(TIME_DAYS) - 1:
                time_i += 1
            elif dim == "size" and size_i < len(SIZE_TOLERANCE) - 1:
                size_i += 1
            else:
                break
            selected = [
                row
                for row in pool
                if _within(
                    row,
                    subject,
                    radius_m=RADIUS_M[radius_i],
                    time_days=TIME_DAYS[time_i],
                    size_tol=SIZE_TOLERANCE[size_i],
                )
            ]
        if len(selected) >= MIN_COMPS:
            break
    return selected
