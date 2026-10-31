from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.results import CoverageStatus, Limitation
from app.modules.property_data.dto import ComparableCandidate
from app.modules.valuation.dto import CompRow, IndexPoint


def dt_param(value: datetime) -> str:
    return value.isoformat()


def candidate_to_comp(row: ComparableCandidate) -> CompRow:
    return CompRow(
        source_row_id=row.source_row_id,
        price_agorot=row.price_agorot,
        size_sqm=row.size_sqm,
        floor=row.floor,
        rooms=row.rooms,
        lon=row.lon,
        lat=row.lat,
        distance_m=row.distance_m,
        effective_at=row.effective_at,
        available_at=row.available_at,
        neighborhood=row.neighborhood,
        statistical_area=row.statistical_area,
    )


def comp_row_payload(row: CompRow) -> dict[str, Any]:
    return {
        "source_row_id": row.source_row_id,
        "price_agorot": row.price_agorot,
        "size_sqm": row.size_sqm,
        "floor": row.floor,
        "rooms": row.rooms,
        "lon": row.lon,
        "lat": row.lat,
        "distance_m": row.distance_m,
        "effective_at": dt_param(row.effective_at),
        "available_at": dt_param(row.available_at),
        "neighborhood": row.neighborhood,
        "statistical_area": row.statistical_area,
    }


def index_point_payload(point: IndexPoint) -> dict[str, Any]:
    return {
        "period_end": dt_param(point.period_end),
        "nis_per_sqm": point.nis_per_sqm,
        "statistical_area": point.statistical_area,
    }


def limitation_payload(limitation: Limitation | None) -> dict[str, Any] | None:
    if limitation is None:
        return None
    return {"code": limitation.code, "message": limitation.message}


def coverage_value(status: CoverageStatus | None) -> str | None:
    if status is None:
        return None
    return status.value
