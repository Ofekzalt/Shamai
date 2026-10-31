from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from statistics import median

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.gis.arcgis import HttpGetClient
from app.modules.evidence.store import upsert_evidence
from app.modules.investigation.tools._helpers import (
    candidate_to_comp,
    coverage_value,
    dt_param,
    index_point_payload,
    limitation_payload,
)
from app.modules.property_data import service as property_data_service
from app.modules.property_data.constants import TRANSACTION_SOURCE
from app.modules.property_data.dto import ComparableCandidatesQuery
from app.modules.valuation.comparables import select_comparables
from app.modules.valuation.dto import Subject
from app.modules.valuation.estimate import estimate_value
from app.modules.valuation.price_index import build_index, time_factor


class FindComparablesResult(BaseModel):
    estimate_value_agorot: int | None
    n_comps: int
    confidence: str | None
    candidate_count: int
    evidence_ids: list[uuid.UUID]


class PriceIndexResult(BaseModel):
    statistical_area: str
    points: list[dict]
    evidence_ids: list[uuid.UUID]


class TransactionDetailResult(BaseModel):
    found: bool
    transaction: dict | None
    evidence_ids: list[uuid.UUID]


class CompareAroundEventResult(BaseModel):
    before_count: int
    after_count: int
    evidence_ids: list[uuid.UUID]


def find_comparables(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    lon: float,
    lat: float,
    as_of: datetime,
    size_sqm: float,
    radius_m: float = 500.0,
    floor: int | None = None,
    rooms: float | None = None,
    source_row_id: str | None = None,
) -> FindComparablesResult:
    query = ComparableCandidatesQuery(
        lon=lon,
        lat=lat,
        radius_m=radius_m,
        as_of=as_of,
    )
    service_result = property_data_service.comparable_candidates(session, client, query)
    comp_rows = [candidate_to_comp(row) for row in service_result.data]
    subject = Subject(
        lon=lon,
        lat=lat,
        size_sqm=size_sqm,
        as_of=as_of,
        floor=floor,
        rooms=rooms,
        source_row_id=source_row_id,
    )
    selected = select_comparables(comp_rows, subject, widen=False, radius_m=radius_m)
    statistical_area = next(
        (row.statistical_area for row in selected if row.statistical_area),
        next((row.statistical_area for row in comp_rows if row.statistical_area), None),
    )
    index_points = (
        build_index(comp_rows, as_of=as_of, statistical_area=statistical_area)
        if statistical_area
        else []
    )
    estimate = estimate_value(
        comp_rows,
        subject,
        index_points=index_points,
        widen=False,
        radius_m=radius_m,
    )
    estimate_payload = None
    if estimate.n_comps > 0:
        estimate_payload = {
            "value_agorot": estimate.value_agorot,
            "iqr_low_agorot": estimate.iqr_low_agorot,
            "iqr_high_agorot": estimate.iqr_high_agorot,
            "n_comps": estimate.n_comps,
            "confidence": estimate.confidence,
        }
    retrieved_at = datetime.now(tz=UTC)
    params = {
        "lon": lon,
        "lat": lat,
        "as_of": dt_param(as_of),
        "size_sqm": size_sqm,
        "radius_m": radius_m,
        "floor": floor,
        "rooms": rooms,
        "source_row_id": source_row_id,
    }
    payload = {
        "candidate_count": len(comp_rows),
        "selected_count": len(selected),
        "estimate": estimate_payload,
        "limitation": limitation_payload(service_result.limitation),
        "coverage_status": coverage_value(service_result.coverage_status),
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="find_comparables",
        params=params,
        payload=payload,
        source=TRANSACTION_SOURCE,
        retrieved_at=retrieved_at,
        coverage_status=coverage_value(service_result.coverage_status),
    )
    return FindComparablesResult(
        estimate_value_agorot=estimate.value_agorot if estimate_payload else None,
        n_comps=estimate.n_comps,
        confidence=estimate.confidence if estimate_payload else None,
        candidate_count=len(comp_rows),
        evidence_ids=[evidence.id],
    )


def price_index(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    lon: float,
    lat: float,
    as_of: datetime,
    statistical_area: str,
    radius_m: float = 2000.0,
) -> PriceIndexResult:
    query = ComparableCandidatesQuery(
        lon=lon,
        lat=lat,
        radius_m=radius_m,
        as_of=as_of,
    )
    service_result = property_data_service.comparable_candidates(session, client, query)
    comp_rows = [candidate_to_comp(row) for row in service_result.data]
    points = build_index(comp_rows, as_of=as_of, statistical_area=statistical_area)
    retrieved_at = datetime.now(tz=UTC)
    params = {
        "lon": lon,
        "lat": lat,
        "as_of": dt_param(as_of),
        "statistical_area": statistical_area,
        "radius_m": radius_m,
    }
    payload = {
        "statistical_area": statistical_area,
        "points": [index_point_payload(point) for point in points],
        "limitation": limitation_payload(service_result.limitation),
        "coverage_status": coverage_value(service_result.coverage_status),
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="price_index",
        params=params,
        payload=payload,
        source=TRANSACTION_SOURCE,
        retrieved_at=retrieved_at,
        coverage_status=coverage_value(service_result.coverage_status),
    )
    return PriceIndexResult(
        statistical_area=statistical_area,
        points=payload["points"],
        evidence_ids=[evidence.id],
    )


def transaction_detail(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    source_row_id: str,
    lon: float,
    lat: float,
    as_of: datetime,
    radius_m: float = 2000.0,
) -> TransactionDetailResult:
    service_result = property_data_service.transaction_detail(
        session,
        client,
        source_row_id=source_row_id,
        lon=lon,
        lat=lat,
        radius_m=radius_m,
        as_of=as_of,
    )
    record = service_result.data
    retrieved_at = datetime.now(tz=UTC)
    params = {
        "source_row_id": source_row_id,
        "lon": lon,
        "lat": lat,
        "as_of": dt_param(as_of),
        "radius_m": radius_m,
    }
    transaction_payload = None
    if record is not None:
        transaction_payload = {
            "source_row_id": record.source_row_id,
            "price_agorot": record.price_agorot,
            "size_sqm": record.size_sqm,
            "rooms": record.rooms,
            "floor": record.floor,
            "neighborhood": record.neighborhood,
            "lon": record.lon,
            "lat": record.lat,
            "effective_at": dt_param(record.effective_at),
            "published_at": dt_param(record.published_at) if record.published_at else None,
        }
    payload = {
        "found": record is not None,
        "transaction": transaction_payload,
        "limitation": limitation_payload(service_result.limitation),
        "coverage_status": coverage_value(service_result.coverage_status),
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="transaction_detail",
        params=params,
        payload=payload,
        source=TRANSACTION_SOURCE,
        retrieved_at=retrieved_at,
        coverage_status=coverage_value(service_result.coverage_status),
    )
    return TransactionDetailResult(
        found=record is not None,
        transaction=transaction_payload,
        evidence_ids=[evidence.id],
    )


def compare_around_event(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    lon: float,
    lat: float,
    as_of: datetime,
    event_at: datetime,
    radius_m: float = 500.0,
    window_days: int = 365,
) -> CompareAroundEventResult:
    window = timedelta(days=window_days)
    query = ComparableCandidatesQuery(
        lon=lon,
        lat=lat,
        radius_m=radius_m,
        as_of=as_of,
    )
    service_result = property_data_service.comparable_candidates(session, client, query)
    comp_rows = [candidate_to_comp(row) for row in service_result.data]
    statistical_area = next(
        (row.statistical_area for row in comp_rows if row.statistical_area),
        None,
    )
    index_points = (
        build_index(comp_rows, as_of=as_of, statistical_area=statistical_area)
        if statistical_area
        else []
    )

    def adjusted_nis_per_sqm(row) -> float | None:
        if row.size_sqm is None or row.size_sqm <= 0:
            return None
        factor, ok = time_factor(index_points, as_of=as_of, sale_at=row.effective_at)
        if not ok:
            return row.price_agorot / row.size_sqm
        return (row.price_agorot * factor) / row.size_sqm

    before: list[float] = []
    after: list[float] = []
    for row in comp_rows:
        if row.effective_at > as_of:
            continue
        value = adjusted_nis_per_sqm(row)
        if value is None:
            continue
        if event_at - window <= row.effective_at < event_at:
            before.append(value)
        elif event_at <= row.effective_at <= event_at + window:
            after.append(value)

    retrieved_at = datetime.now(tz=UTC)
    params = {
        "lon": lon,
        "lat": lat,
        "as_of": dt_param(as_of),
        "event_at": dt_param(event_at),
        "radius_m": radius_m,
        "window_days": window_days,
    }
    payload = {
        "correlation_not_causation": True,
        "index_adjusted": bool(index_points),
        "statistical_area": statistical_area,
        "before": {
            "count": len(before),
            "median_nis_per_sqm": median(before) if before else None,
        },
        "after": {
            "count": len(after),
            "median_nis_per_sqm": median(after) if after else None,
        },
        "limitation": limitation_payload(service_result.limitation),
        "coverage_status": coverage_value(service_result.coverage_status),
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="compare_around_event",
        params=params,
        payload=payload,
        source=TRANSACTION_SOURCE,
        retrieved_at=retrieved_at,
        coverage_status=coverage_value(service_result.coverage_status),
    )
    return CompareAroundEventResult(
        before_count=len(before),
        after_count=len(after),
        evidence_ids=[evidence.id],
    )
