from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Confidence = Literal["ok", "thin", "limited_index"]


@dataclass(frozen=True)
class Subject:
    lon: float
    lat: float
    size_sqm: float
    as_of: datetime
    floor: int | None = None
    rooms: float | None = None
    neighborhood: str | None = None
    source_row_id: str | None = None


@dataclass(frozen=True)
class CompRow:
    source_row_id: str
    price_agorot: int
    size_sqm: float | None
    floor: int | None
    rooms: float | None
    lon: float
    lat: float
    distance_m: float
    effective_at: datetime
    available_at: datetime
    neighborhood: str | None
    statistical_area: str | None


@dataclass(frozen=True)
class IndexPoint:
    period_end: datetime
    nis_per_sqm: float
    statistical_area: str


@dataclass(frozen=True)
class Adjustment:
    factor: float
    reason: str


@dataclass(frozen=True)
class Estimate:
    value_agorot: int
    iqr_low_agorot: int
    iqr_high_agorot: int
    n_comps: int
    confidence: Confidence
