from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.infrastructure.gis.coverage_grid import (
    cells_for_radius,
    lon_lat_to_cell,
    open_window_stale,
)


def test_lon_lat_to_cell_is_stable() -> None:
    first = lon_lat_to_cell(34.7818, 32.0853)
    second = lon_lat_to_cell(34.7818, 32.0853)
    assert first == second


def test_cells_for_radius_covers_center_and_grows() -> None:
    lon, lat = 34.7818, 32.0853
    tight = cells_for_radius(lon, lat, 50)
    wide = cells_for_radius(lon, lat, 600)
    assert lon_lat_to_cell(lon, lat) in tight
    assert tight <= wide
    assert len(wide) > len(tight)


def test_closed_historical_window_is_not_stale() -> None:
    now = datetime(2026, 10, 31, tzinfo=UTC)
    requested_end = datetime(2025, 1, 1, tzinfo=UTC)
    assert not open_window_stale(
        window_end=requested_end,
        lag_days=90,
        now=now,
        requested_end=requested_end,
    )


def test_recent_open_window_past_lag_is_stale() -> None:
    now = datetime(2026, 10, 31, tzinfo=UTC)
    window_end = now - timedelta(days=120)
    assert open_window_stale(
        window_end=window_end,
        lag_days=90,
        now=now,
        requested_end=now,
    )
