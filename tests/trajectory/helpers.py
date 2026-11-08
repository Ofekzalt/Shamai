from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from geoalchemy2 import WKTElement
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.point_in_time import compute_available_at
from app.modules.investigation.graph.builder import build_graph
from app.modules.investigation.graph.runtime import RUNTIME_KEY, GraphRuntime
from app.modules.planning.constants import IPLAN_SOURCE, RENEWAL_SOURCE
from app.modules.planning.models import Plan, PlanStatusEvent
from app.modules.planning.repository import upsert_renewal_polygon
from app.modules.property_data.constants import TRANSACTION_LAG_DAYS
from app.modules.property_data.dto import GeocodeRecord, TransactionRecord
from app.modules.property_data.repository import upsert_geocode, upsert_transaction

ORIGIN_LON = 34.7818
ORIGIN_LAT = 32.0853
AS_OF = datetime(2025, 1, 1, tzinfo=UTC)
POLYGON = "MULTIPOLYGON(((34.78 32.08,34.79 32.08,34.79 32.09,34.78 32.09,34.78 32.08)))"


def offline_client() -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "offline"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def seed_geocode(session: Session, *, street: str = "Rothschild", house_number: str = "1") -> None:
    upsert_geocode(
        session,
        GeocodeRecord(
            street=street,
            house_number=house_number,
            lon=ORIGIN_LON,
            lat=ORIGIN_LAT,
            source="tlv_municipal",
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            neighborhood="test",
        ),
    )


def seed_transaction(
    session: Session,
    *,
    source_row_id: str,
    lon: float,
    lat: float,
    price_agorot: int,
    size_sqm: float = 80.0,
    effective: datetime | None = None,
) -> None:
    effective = effective or datetime(2024, 6, 1, tzinfo=UTC)
    published = datetime(2024, 7, 1, tzinfo=UTC)
    record = TransactionRecord(
        source_row_id=source_row_id,
        price_agorot=price_agorot,
        size_sqm=size_sqm,
        rooms=3.0,
        floor=2,
        neighborhood="test",
        lon=lon,
        lat=lat,
        effective_at=effective,
        published_at=published,
    )
    available_at, estimated = compute_available_at(
        effective_at=effective,
        published_at=published,
        lag_days=TRANSACTION_LAG_DAYS,
    )
    upsert_transaction(
        session,
        record,
        available_at=available_at,
        available_at_estimated=estimated,
        retrieved_at=published,
    )


def seed_plan(
    session: Session,
    *,
    pl_number: str,
    status: str,
    source: str = IPLAN_SOURCE,
) -> uuid.UUID:
    plan = Plan(
        id=uuid.uuid4(),
        source=source,
        pl_number=pl_number,
        mp_id=None,
        name=pl_number,
        geom=WKTElement(POLYGON, srid=4326),
    )
    session.add(plan)
    session.flush()
    session.add(
        PlanStatusEvent(
            id=uuid.uuid4(),
            plan_id=plan.id,
            source=source,
            status=status,
            effective_at=datetime(2024, 1, 1, tzinfo=UTC),
            published_at=datetime(2024, 1, 1, tzinfo=UTC),
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            available_at=datetime(2024, 1, 1, tzinfo=UTC),
            available_at_estimated=False,
        )
    )
    session.flush()
    return plan.id


def seed_renewal(session: Session, *, status: str = "approved") -> None:
    upsert_renewal_polygon(
        session,
        source=RENEWAL_SOURCE,
        source_feature_id="r1",
        taba="taba-1",
        snapshot_status=status,
        wkt=POLYGON,
        effective_at=datetime(2024, 1, 1, tzinfo=UTC),
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
        retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
        available_at=datetime(2024, 1, 1, tzinfo=UTC),
        available_at_estimated=False,
        history_available=True,
    )


def run_rules(session: Session, request: dict) -> dict:
    runtime = GraphRuntime(
        session_factory=lambda: session,
        http=offline_client(),
        settings=get_settings(),
        llm=None,
        owns_sessions=False,
    )
    graph = build_graph("rules", checkpointer=MemorySaver())
    job_id = str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": job_id, RUNTIME_KEY: runtime},
        "max_concurrency": 1,
    }
    return graph.invoke({"job_id": job_id, "request": request}, config=config)


def request_body(**overrides: object) -> dict:
    body = {
        "address": "Rothschild 1",
        "asking_price_agorot": 4_000_000_00,
        "size_sqm": 80.0,
        "profile": "homebuyer",
        "as_of": "2025-01-01",
    }
    body.update(overrides)
    return body
