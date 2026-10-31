from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.point_in_time import compute_available_at
from app.main import app
from app.modules.investigation.tools import market
from app.modules.property_data.constants import TRANSACTION_LAG_DAYS
from app.modules.property_data.dto import TransactionRecord
from app.modules.property_data.repository import upsert_transaction


def _upsert_comp(session: Session) -> None:
    record = TransactionRecord(
        source_row_id="api-comp",
        price_agorot=400_000_000,
        size_sqm=80.0,
        rooms=3.0,
        floor=2,
        neighborhood="test",
        lon=34.7823,
        lat=32.0853,
        effective_at=datetime(2024, 3, 1, tzinfo=UTC),
    )
    available_at, estimated = compute_available_at(
        effective_at=record.effective_at,
        published_at=datetime(2024, 6, 1, tzinfo=UTC),
        lag_days=TRANSACTION_LAG_DAYS,
    )
    upsert_transaction(
        session,
        record,
        available_at=available_at,
        available_at_estimated=estimated,
        retrieved_at=datetime(2024, 6, 1, tzinfo=UTC),
    )


def test_get_evidence_returns_payload(db_session: Session) -> None:
    _upsert_comp(db_session)
    db_session.flush()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "offline"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    tool_result = market.find_comparables(
        db_session,
        client,
        run_id=uuid.uuid4(),
        lon=34.7818,
        lat=32.0853,
        as_of=datetime(2025, 1, 1, tzinfo=UTC),
        size_sqm=80.0,
        radius_m=2000.0,
    )
    evidence_id = tool_result.evidence_ids[0]

    def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as api_client:
        response = api_client.get(f"/evidence/{evidence_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(evidence_id)
    assert body["tool_name"] == "find_comparables"
    assert "estimate" in body["payload"]
