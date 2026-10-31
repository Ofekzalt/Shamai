from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select

from app.core.point_in_time import compute_available_at
from app.modules.evidence.models import Evidence
from app.modules.investigation.tools import market
from app.modules.property_data.constants import TRANSACTION_LAG_DAYS
from app.modules.property_data.dto import TransactionRecord
from app.modules.property_data.repository import upsert_transaction


def _upsert(
    session,
    *,
    source_row_id: str,
    lon: float,
    lat: float,
    available: datetime,
    effective: datetime,
    price_agorot: int = 400_000_000,
) -> None:
    record = TransactionRecord(
        source_row_id=source_row_id,
        price_agorot=price_agorot,
        size_sqm=80.0,
        rooms=3.0,
        floor=2,
        neighborhood="test",
        lon=lon,
        lat=lat,
        effective_at=effective,
    )
    available_at, estimated = compute_available_at(
        effective_at=effective,
        published_at=available,
        lag_days=TRANSACTION_LAG_DAYS,
    )
    upsert_transaction(
        session,
        record,
        available_at=available_at,
        available_at_estimated=estimated,
        retrieved_at=available,
    )


def _offline_client() -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "offline"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_find_comparables_idempotent_evidence(db_session) -> None:
    origin_lon, origin_lat = 34.7818, 32.0853
    _upsert(
        db_session,
        source_row_id="comp-1",
        lon=origin_lon + 0.0005,
        lat=origin_lat,
        available=datetime(2024, 6, 1, tzinfo=UTC),
        effective=datetime(2024, 3, 1, tzinfo=UTC),
    )
    db_session.flush()
    run_id = uuid.uuid4()
    as_of = datetime(2025, 1, 1, tzinfo=UTC)
    client = _offline_client()
    first = market.find_comparables(
        db_session,
        client,
        run_id=run_id,
        lon=origin_lon,
        lat=origin_lat,
        as_of=as_of,
        size_sqm=80.0,
        radius_m=2000.0,
    )
    second = market.find_comparables(
        db_session,
        client,
        run_id=run_id,
        lon=origin_lon,
        lat=origin_lat,
        as_of=as_of,
        size_sqm=80.0,
        radius_m=2000.0,
    )
    assert first.evidence_ids == second.evidence_ids
    count = db_session.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.run_id == run_id)
    )
    assert count == 1


def test_find_comparables_hides_future_transaction(db_session) -> None:
    origin_lon, origin_lat = 34.7818, 32.0853
    _upsert(
        db_session,
        source_row_id="future",
        lon=origin_lon + 0.0002,
        lat=origin_lat,
        available=datetime(2026, 1, 1, tzinfo=UTC),
        effective=datetime(2025, 6, 1, tzinfo=UTC),
    )
    db_session.flush()
    result = market.find_comparables(
        db_session,
        _offline_client(),
        run_id=uuid.uuid4(),
        lon=origin_lon,
        lat=origin_lat,
        as_of=datetime(2025, 1, 1, tzinfo=UTC),
        size_sqm=80.0,
        radius_m=2000.0,
    )
    assert result.candidate_count == 0


def test_find_comparables_stores_limitation_not_zero(db_session) -> None:
    origin_lon, origin_lat = 34.7818, 32.0853
    result = market.find_comparables(
        db_session,
        _offline_client(),
        run_id=uuid.uuid4(),
        lon=origin_lon,
        lat=origin_lat,
        as_of=datetime(2025, 1, 1, tzinfo=UTC),
        size_sqm=80.0,
        radius_m=500.0,
    )
    row = db_session.get(Evidence, result.evidence_ids[0])
    assert row is not None
    assert row.payload["limitation"] is not None
    assert row.coverage_status == "incomplete"
    assert row.payload["estimate"] is None
    assert result.estimate_value_agorot is None


def test_compare_around_event_marks_non_causal(db_session) -> None:
    origin_lon, origin_lat = 34.7818, 32.0853
    event_at = datetime(2024, 6, 1, tzinfo=UTC)
    _upsert(
        db_session,
        source_row_id="before",
        lon=origin_lon + 0.0003,
        lat=origin_lat,
        available=datetime(2024, 2, 1, tzinfo=UTC),
        effective=datetime(2024, 1, 15, tzinfo=UTC),
    )
    _upsert(
        db_session,
        source_row_id="after",
        lon=origin_lon + 0.0004,
        lat=origin_lat,
        available=datetime(2024, 8, 1, tzinfo=UTC),
        effective=datetime(2024, 7, 1, tzinfo=UTC),
    )
    db_session.flush()
    result = market.compare_around_event(
        db_session,
        _offline_client(),
        run_id=uuid.uuid4(),
        lon=origin_lon,
        lat=origin_lat,
        as_of=datetime(2025, 1, 1, tzinfo=UTC),
        event_at=event_at,
        radius_m=2000.0,
    )
    row = db_session.get(Evidence, result.evidence_ids[0])
    assert row is not None
    assert row.payload["correlation_not_causation"] is True
