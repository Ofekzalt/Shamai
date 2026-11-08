from __future__ import annotations

from app.modules.investigation.tools.market import (
    MIN_COMPS,
    RADIUS_M,
    SIZE_TOLERANCE,
    TIME_DAYS,
    WIDEN_ORDER,
)


def initial_search_window() -> dict[str, float | int]:
    return {
        "radius_m": RADIUS_M[0],
        "time_days": TIME_DAYS[0],
        "size_tol": SIZE_TOLERANCE[0],
    }


def next_search_window(
    *,
    n_comps: int,
    radius_m: float,
    time_days: int,
    size_tol: float,
) -> dict[str, float | int] | None:
    if n_comps >= MIN_COMPS:
        return None
    radius_i = list(RADIUS_M).index(radius_m) if radius_m in RADIUS_M else 0
    time_i = list(TIME_DAYS).index(time_days) if time_days in TIME_DAYS else 0
    size_i = list(SIZE_TOLERANCE).index(size_tol) if size_tol in SIZE_TOLERANCE else 0
    for dim in WIDEN_ORDER:
        if dim == "radius" and radius_i < len(RADIUS_M) - 1:
            return {
                "radius_m": RADIUS_M[radius_i + 1],
                "time_days": time_days,
                "size_tol": size_tol,
            }
        if dim == "time" and time_i < len(TIME_DAYS) - 1 and radius_i == len(RADIUS_M) - 1:
            return {
                "radius_m": radius_m,
                "time_days": TIME_DAYS[time_i + 1],
                "size_tol": size_tol,
            }
        if (
            dim == "size"
            and size_i < len(SIZE_TOLERANCE) - 1
            and radius_i == len(RADIUS_M) - 1
            and time_i == len(TIME_DAYS) - 1
        ):
            return {
                "radius_m": radius_m,
                "time_days": time_days,
                "size_tol": SIZE_TOLERANCE[size_i + 1],
            }
    return None
