from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.investigation.graph.address import parse_address
from app.modules.planning.repository import (
    list_plans_at_point_as_of,
    list_renewal_polygons_at_point_as_of,
)
from app.modules.property_data.repository import get_geocode, list_knn_candidates
from app.modules.valuation.constants import MIN_COMPS, RADIUS_M


class PropertyExpectation(BaseModel):
    property_id: str
    geocoded: bool
    lon: float | None = None
    lat: float | None = None
    knn_candidates: int = 0
    min_comps_met: bool = False
    plan_count: int = 0
    plan_sources: list[str] = []
    renewal_present: bool = False
    plan_source_conflict: bool = False


def _parse_as_of(value: str) -> datetime:
    if len(value) == 10:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def expected_for_case(session: Session, case: dict[str, Any]) -> PropertyExpectation:
    property_id = str(case["id"])
    street, house_number = parse_address(str(case["address"]))
    as_of = _parse_as_of(str(case["as_of"]))
    cached = get_geocode(session, street=street, house_number=house_number)
    if cached is None:
        return PropertyExpectation(property_id=property_id, geocoded=False)

    lon = float(cached.lon)
    lat = float(cached.lat)
    knn = list_knn_candidates(
        session,
        lon=lon,
        lat=lat,
        radius_m=float(RADIUS_M[0]),
        as_of=as_of,
        limit=50,
    )
    plans = list_plans_at_point_as_of(session, lon=lon, lat=lat, as_of=as_of)
    renewals = list_renewal_polygons_at_point_as_of(session, lon=lon, lat=lat, as_of=as_of)
    sources = sorted({plan.source for plan, _event in plans})
    statuses_by_source: dict[str, set[str]] = {}
    for plan, event in plans:
        statuses_by_source.setdefault(plan.source, set()).add(event.status)
    conflict = len(sources) > 1 and any(
        len(statuses) > 1 for statuses in statuses_by_source.values()
    )

    return PropertyExpectation(
        property_id=property_id,
        geocoded=True,
        lon=lon,
        lat=lat,
        knn_candidates=len(knn),
        min_comps_met=len(knn) >= MIN_COMPS,
        plan_count=len(plans),
        plan_sources=sources,
        renewal_present=bool(renewals),
        plan_source_conflict=conflict,
    )
