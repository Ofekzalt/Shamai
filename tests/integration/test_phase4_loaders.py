from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.point_in_time import compute_available_at
from app.core.results import CoverageStatus
from app.modules.planning.dto import PlansAtPointQuery
from app.modules.planning.repository import upsert_plan, upsert_plan_status_event
from app.modules.planning.service import plans_at_point
from app.modules.property_data.constants import TRANSACTION_LAG_DAYS
from app.modules.property_data.dto import NearbyTransactionsQuery, TransactionRecord
from app.modules.property_data.repository import upsert_transaction
from app.modules.property_data.service import nearby_transactions


def test_nearby_returns_limitation_without_complete_coverage(db_session) -> None:
    record = TransactionRecord(
        source_row_id="row-1",
        price_agorot=1_000_000,
        size_sqm=80.0,
        rooms=3.0,
        floor=2,
        neighborhood="test",
        lon=34.7818,
        lat=32.0853,
        effective_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    available_at, estimated = compute_available_at(
        effective_at=record.effective_at,
        published_at=None,
        lag_days=TRANSACTION_LAG_DAYS,
    )
    upsert_transaction(
        db_session,
        record,
        available_at=available_at,
        available_at_estimated=estimated,
        retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    db_session.flush()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "offline"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    as_of = datetime(2025, 1, 1, tzinfo=UTC)
    result = nearby_transactions(
        db_session,
        client,
        NearbyTransactionsQuery(lon=34.7818, lat=32.0853, radius_m=500, as_of=as_of),
    )
    assert result.limitation is not None
    assert result.coverage_status == CoverageStatus.INCOMPLETE


def test_plans_at_point_requires_visible_status_event(db_session) -> None:
    polygon = "MULTIPOLYGON(((34.78 32.08,34.79 32.08,34.79 32.09,34.78 32.09,34.78 32.08)))"
    plan_id = upsert_plan(
        db_session,
        source="iplan",
        pl_number="P-1",
        mp_id=None,
        name="Test",
        wkt=polygon,
    )
    effective = datetime(2024, 12, 15, tzinfo=UTC)
    published = datetime(2025, 1, 15, tzinfo=UTC)
    upsert_plan_status_event(
        db_session,
        plan_id=plan_id,
        source="iplan",
        status="approved",
        effective_at=effective,
        published_at=published,
        retrieved_at=published,
        available_at=published,
        available_at_estimated=False,
    )
    db_session.flush()

    def empty_arcgis(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"features": []})

    client = httpx.Client(transport=httpx.MockTransport(empty_arcgis))
    before = plans_at_point(
        db_session,
        client,
        PlansAtPointQuery(lon=34.785, lat=32.085, as_of=datetime(2024, 11, 1, tzinfo=UTC)),
    )
    after = plans_at_point(
        db_session,
        client,
        PlansAtPointQuery(lon=34.785, lat=32.085, as_of=datetime(2025, 2, 1, tzinfo=UTC)),
    )
    assert before.data == []
    assert len(after.data) == 1
    assert after.data[0].status == "approved"
