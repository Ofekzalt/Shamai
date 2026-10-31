from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.property_data.dto import ComparableCandidate
from evals.valuation.metrics import score
from evals.valuation.run import run
from evals.valuation.splits import temporal_holdout


def test_temporal_holdout_uses_available_at() -> None:
    as_of = datetime(2025, 1, 1, tzinfo=UTC)

    def sale(row_id: str, available: datetime) -> ComparableCandidate:
        return ComparableCandidate(
            source_row_id=row_id,
            price_agorot=1,
            size_sqm=80.0,
            rooms=3.0,
            floor=1,
            neighborhood="x",
            lon=34.78,
            lat=32.08,
            distance_m=0.0,
            effective_at=available,
            available_at=available,
            statistical_area=None,
        )

    train, test = temporal_holdout(
        [
            sale("old", as_of - timedelta(days=400)),
            sale("hold", as_of - timedelta(days=10)),
        ],
        as_of=as_of,
    )
    assert [r.source_row_id for r in train] == ["old"]
    assert [r.source_row_id for r in test] == ["hold"]


def test_run_exits_one_when_no_transactions(monkeypatch) -> None:
    monkeypatch.setattr(
        "evals.valuation.run.list_geolocated_transactions_as_of",
        lambda _session, _as_of: [],
    )
    assert run(session=object()) == 1


def test_score_within_ten() -> None:
    metrics = score([100, 100], [100, 120])
    assert metrics.n == 2
    assert metrics.within_10 == 0.5
    assert metrics.mae_agorot == 10
