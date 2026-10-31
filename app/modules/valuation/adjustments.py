from __future__ import annotations

from .constants import FLOOR_ADJUST_MAX, FLOOR_ADJUST_MIN, FLOOR_ADJUST_PER_LEVEL
from .dto import Adjustment


def size_adjustment(*, subject_size_sqm: float, comp_size_sqm: float) -> Adjustment:
    factor = subject_size_sqm / comp_size_sqm
    return Adjustment(factor=factor, reason="scale to subject size")


def floor_adjustment(*, subject_floor: int | None, comp_floor: int | None) -> Adjustment:
    if subject_floor is None or comp_floor is None:
        return Adjustment(factor=1.0, reason="floor unknown")
    raw = 1.0 + FLOOR_ADJUST_PER_LEVEL * (subject_floor - comp_floor)
    factor = min(FLOOR_ADJUST_MAX, max(FLOOR_ADJUST_MIN, raw))
    return Adjustment(factor=factor, reason="1% per floor difference, clamped")
