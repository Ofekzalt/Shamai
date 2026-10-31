from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.point_in_time import compute_available_at
from app.core.results import CoverageStatus
from app.modules.property_data.constants import TRANSACTION_LAG_DAYS
from app.modules.property_data.dto import ComparableCandidatesQuery, TransactionRecord
from app.modules.property_data.repository import upsert_transaction
from app.modules.property_data.service import comparable_candidates


def _upsert(
    session,
    *,
    source_row_id: str,
    lon: float,
    lat: float,
    available: datetime,
    effective: datetime,
) -> None:
    record = TransactionRecord(
        source_row_id=source_row_id,
        price_agorot=400_000_000,
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


def test_knn_orders_by_distance_and_hides_future(db_session) -> None:
    origin_lon, origin_lat = 34.7818, 32.0853
    _upsert(
        db_session,
        source_row_id="near",
        lon=origin_lon + 0.0005,
        lat=origin_lat,
        available=datetime(2024, 6, 1, tzinfo=UTC),
        effective=datetime(2024, 3, 1, tzinfo=UTC),
    )
    _upsert(
        db_session,
        source_row_id="far",
        lon=origin_lon + 0.004,
        lat=origin_lat,
        available=datetime(2024, 6, 1, tzinfo=UTC),
        effective=datetime(2024, 3, 1, tzinfo=UTC),
    )
    _upsert(
        db_session,
        source_row_id="future",
        lon=origin_lon + 0.0002,
        lat=origin_lat,
        available=datetime(2026, 1, 1, tzinfo=UTC),
        effective=datetime(2025, 6, 1, tzinfo=UTC),
    )
    db_session.flush()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "offline"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = comparable_candidates(
        db_session,
        client,
        ComparableCandidatesQuery(
            lon=origin_lon,
            lat=origin_lat,
            radius_m=2000,
            as_of=datetime(2025, 1, 1, tzinfo=UTC),
        ),
    )
    ids = [row.source_row_id for row in result.data]
    assert "future" not in ids
    assert ids[:2] == ["near", "far"]
    assert result.data[0].distance_m < result.data[1].distance_m
    assert result.coverage_status == CoverageStatus.INCOMPLETE
    assert result.limitation is not None
