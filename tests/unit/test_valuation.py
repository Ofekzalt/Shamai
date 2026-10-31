from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.valuation.adjustments import floor_adjustment, size_adjustment
from app.modules.valuation.baseline import baseline_value
from app.modules.valuation.comparables import select_comparables
from app.modules.valuation.constants import MIN_COMPS
from app.modules.valuation.dto import CompRow, Subject
from app.modules.valuation.estimate import estimate_value
from app.modules.valuation.price_index import build_index, time_factor


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def _row(
    *,
    source_row_id: str,
    price_agorot: int = 400_000_000,
    size_sqm: float = 80.0,
    floor: int | None = 3,
    lon: float = 34.7818,
    lat: float = 32.0853,
    distance_m: float = 100.0,
    effective_at: datetime | None = None,
    available_at: datetime | None = None,
    neighborhood: str | None = "לב העיר",
    statistical_area: str | None = "5001",
) -> CompRow:
    effective = effective_at or _dt(2024, 1, 1)
    available = available_at or effective + timedelta(days=90)
    return CompRow(
        source_row_id=source_row_id,
        price_agorot=price_agorot,
        size_sqm=size_sqm,
        floor=floor,
        rooms=3.0,
        lon=lon,
        lat=lat,
        distance_m=distance_m,
        effective_at=effective,
        available_at=available,
        neighborhood=neighborhood,
        statistical_area=statistical_area,
    )


def _subject(**kwargs: object) -> Subject:
    defaults: dict[str, object] = {
        "lon": 34.7818,
        "lat": 32.0853,
        "size_sqm": 80.0,
        "floor": 3,
        "rooms": 3.0,
        "as_of": _dt(2025, 1, 1),
        "neighborhood": "לב העיר",
        "source_row_id": "subject",
    }
    defaults.update(kwargs)
    return Subject(**defaults)  # type: ignore[arg-type]


def test_select_drops_future_available_at() -> None:
    subject = _subject()
    future = _row(
        source_row_id="future",
        available_at=_dt(2025, 6, 1),
        effective_at=_dt(2024, 6, 1),
    )
    ok = _row(source_row_id="ok")
    selected = select_comparables([future, ok], subject)
    assert [r.source_row_id for r in selected] == ["ok"]


def test_select_excludes_subject_sale() -> None:
    subject = _subject(source_row_id="self")
    own = _row(source_row_id="self")
    other = _row(source_row_id="other")
    selected = select_comparables([own, other], subject)
    assert [r.source_row_id for r in selected] == ["other"]


def test_select_widens_radius_before_time() -> None:
    subject = _subject(as_of=_dt(2025, 1, 1))
    old_close = [
        _row(
            source_row_id=f"old{i}",
            distance_m=100.0,
            effective_at=_dt(2023, 1, 1),
            available_at=_dt(2023, 4, 1),
        )
        for i in range(MIN_COMPS)
    ]
    recent_far = [
        _row(
            source_row_id=f"recent{i}",
            distance_m=1500.0,
            effective_at=_dt(2024, 10, 1),
            available_at=_dt(2024, 12, 1),
        )
        for i in range(MIN_COMPS)
    ]
    selected = select_comparables(old_close + recent_far, subject)
    assert len(selected) >= MIN_COMPS
    assert all(r.source_row_id.startswith("recent") for r in selected)


def test_index_excludes_subject_from_time_factor() -> None:
    as_of = _dt(2025, 1, 1)
    sale_at = _dt(2024, 6, 1)
    base_rows = [
        _row(
            source_row_id="c1",
            price_agorot=400_000_000,
            effective_at=_dt(2024, 1, 1),
            available_at=_dt(2024, 4, 1),
        ),
        _row(
            source_row_id="c2",
            price_agorot=420_000_000,
            effective_at=_dt(2024, 3, 1),
            available_at=_dt(2024, 6, 1),
        ),
        _row(
            source_row_id="c3",
            price_agorot=430_000_000,
            effective_at=_dt(2024, 10, 1),
            available_at=_dt(2024, 12, 1),
        ),
    ]
    with_subject = base_rows + [
        _row(
            source_row_id="subject",
            price_agorot=900_000_000,
            effective_at=sale_at,
            available_at=as_of,
        )
    ]
    without = build_index(base_rows, as_of=as_of, statistical_area="5001")
    with_leak = build_index(with_subject, as_of=as_of, statistical_area="5001")
    filtered = [r for r in with_subject if r.source_row_id != "subject"]
    factor_clean, _ = time_factor(without, as_of=as_of, sale_at=sale_at)
    factor_leak, _ = time_factor(with_leak, as_of=as_of, sale_at=sale_at)
    factor_filtered, _ = time_factor(
        build_index(filtered, as_of=as_of, statistical_area="5001"),
        as_of=as_of,
        sale_at=sale_at,
    )
    assert factor_clean != factor_leak
    assert factor_filtered == factor_clean


def test_select_widens_until_min_comps() -> None:
    subject = _subject()
    close = [_row(source_row_id=f"c{i}", distance_m=100.0) for i in range(2)]
    far = [_row(source_row_id=f"f{i}", distance_m=1500.0) for i in range(MIN_COMPS)]
    selected = select_comparables(close + far, subject)
    assert len(selected) >= MIN_COMPS
    assert {r.source_row_id for r in selected} >= {f"c{i}" for i in range(2)}


def test_size_adjustment_scales_to_subject() -> None:
    adj = size_adjustment(subject_size_sqm=100.0, comp_size_sqm=80.0)
    assert adj.factor == 100.0 / 80.0
    assert adj.reason


def test_floor_adjustment_clamped_and_unknown() -> None:
    up = floor_adjustment(subject_floor=8, comp_floor=1)
    assert up.factor == 1.05
    missing = floor_adjustment(subject_floor=None, comp_floor=2)
    assert missing.factor == 1.0
    assert "unknown" in missing.reason


def test_index_ignores_future_months() -> None:
    as_of = _dt(2024, 6, 15)
    rows = [
        _row(
            source_row_id="old",
            price_agorot=400_000_000,
            size_sqm=80.0,
            effective_at=_dt(2024, 1, 10),
            available_at=_dt(2024, 4, 1),
        ),
        _row(
            source_row_id="future",
            price_agorot=800_000_000,
            size_sqm=80.0,
            effective_at=_dt(2024, 8, 10),
            available_at=_dt(2024, 9, 1),
        ),
    ]
    series = build_index(rows, as_of=as_of, statistical_area="5001")
    assert all(p.period_end <= as_of for p in series)
    factor, used = time_factor(
        series,
        as_of=as_of,
        sale_at=_dt(2024, 1, 10),
    )
    assert used
    assert factor == 1.0


def test_estimate_respects_widen_false_radius() -> None:
    subject = _subject()
    near = [
        _row(
            source_row_id=f"near{i}",
            distance_m=100.0,
            effective_at=_dt(2024, 10, 1),
            available_at=_dt(2024, 12, 1),
        )
        for i in range(MIN_COMPS)
    ]
    far = [
        _row(
            source_row_id=f"far{i}",
            distance_m=1500.0,
            effective_at=_dt(2024, 10, 1),
            available_at=_dt(2024, 12, 1),
        )
        for i in range(3)
    ]
    defaulted = estimate_value(near + far, subject, index_points=[])
    assert defaulted.n_comps == MIN_COMPS
    unwidened = estimate_value(
        near + far,
        subject,
        index_points=[],
        widen=False,
        radius_m=2000.0,
    )
    assert unwidened.n_comps == MIN_COMPS + 3


def test_estimate_thin_when_fewer_than_min_comps() -> None:
    subject = _subject()
    rows = [_row(source_row_id="only")]
    result = estimate_value(rows, subject, index_points=[])
    assert result.n_comps == 1
    assert result.confidence == "thin"
    assert result.value_agorot > 0


def test_baseline_is_neighborhood_median_times_size() -> None:
    subject = _subject(size_sqm=100.0, as_of=_dt(2025, 1, 1))
    rows = [
        _row(source_row_id="a", price_agorot=400_000_000, size_sqm=80.0),
        _row(source_row_id="b", price_agorot=480_000_000, size_sqm=80.0),
        _row(
            source_row_id="other-hood",
            price_agorot=900_000_000,
            size_sqm=80.0,
            neighborhood="צפון",
        ),
    ]
    value = baseline_value(rows, subject)
    assert value == 5_500_000 * 100
