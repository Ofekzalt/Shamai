from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.point_in_time import compute_available_at, visible_as_of
from app.modules.planning.models import PlanStatusEvent


def test_visible_as_of_filters_on_available_at() -> None:
    as_of = datetime(2024, 11, 1, tzinfo=UTC)
    stmt = visible_as_of(select(PlanStatusEvent), as_of)
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "plan_status_events.available_at" in compiled
    assert "<=" in compiled


def test_compute_available_at_uses_published_at_when_present() -> None:
    effective = datetime(2024, 12, 15, tzinfo=UTC)
    published = datetime(2025, 1, 10, tzinfo=UTC)
    available, estimated = compute_available_at(
        effective_at=effective,
        published_at=published,
        lag_days=14,
    )
    assert available == published
    assert estimated is False


def test_compute_available_at_applies_lag_when_published_missing() -> None:
    effective = datetime(2024, 12, 15, tzinfo=UTC)
    available, estimated = compute_available_at(
        effective_at=effective,
        published_at=None,
        lag_days=14,
    )
    assert available == datetime(2024, 12, 29, tzinfo=UTC)
    assert estimated is True
