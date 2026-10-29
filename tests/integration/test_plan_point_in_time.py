from __future__ import annotations

import uuid
from datetime import UTC, datetime

from geoalchemy2 import WKTElement

from app.modules.planning.models import Plan, PlanStatusEvent
from app.modules.planning.repository import list_status_events_as_of

TZ = UTC
FIXTURE_POLYGON = "MULTIPOLYGON(((34.78 32.08,34.79 32.08,34.79 32.09,34.78 32.09,34.78 32.08)))"


def test_plan_status_event_respects_available_at_not_effective_at(db_session) -> None:
    plan = Plan(
        id=uuid.uuid4(),
        source="iplan",
        pl_number="TEST-001",
        mp_id=None,
        name="Fixture plan",
        geom=WKTElement(FIXTURE_POLYGON, srid=4326),
    )
    db_session.add(plan)
    db_session.flush()

    effective_at = datetime(2024, 12, 15, tzinfo=TZ)
    published_at = datetime(2025, 1, 15, tzinfo=TZ)
    retrieved_at = datetime(2025, 1, 20, tzinfo=TZ)

    event = PlanStatusEvent(
        id=uuid.uuid4(),
        plan_id=plan.id,
        source="iplan",
        status="approved",
        effective_at=effective_at,
        published_at=published_at,
        retrieved_at=retrieved_at,
        available_at=published_at,
        available_at_estimated=False,
    )
    db_session.add(event)
    db_session.flush()

    before = list_status_events_as_of(db_session, plan.id, datetime(2024, 11, 1, tzinfo=TZ))
    after_deal_before_publish = list_status_events_as_of(
        db_session,
        plan.id,
        datetime(2024, 12, 20, tzinfo=TZ),
    )
    after = list_status_events_as_of(db_session, plan.id, datetime(2025, 2, 1, tzinfo=TZ))

    assert before == []
    assert after_deal_before_publish == []
    assert len(after) == 1
    assert after[0].status == "approved"
