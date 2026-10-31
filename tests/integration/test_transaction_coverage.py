from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.infrastructure.gis.coverage_grid import cells_for_radius, lon_lat_to_cell
from app.modules.property_data.constants import TRANSACTION_SOURCE
from app.modules.property_data.repository import get_coverage_cells
from app.modules.property_data.service_transactions import ensure_transactions_loaded


def test_city_fetch_marks_all_radius_cells_once(db_session) -> None:
    lon, lat = 34.7818, 32.0853
    radius_m = 600.0
    cells = cells_for_radius(lon, lat, radius_m)
    assert len(cells) >= 2
    assert lon_lat_to_cell(lon, lat) in cells
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200,
            json={"result": {"records": [], "total": 0}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    as_of = datetime(2025, 1, 1, tzinfo=UTC)
    window_start = as_of.replace(year=as_of.year - 2)
    first = ensure_transactions_loaded(
        db_session,
        client,
        lon=lon,
        lat=lat,
        radius_m=radius_m,
        window_start=window_start,
        window_end=as_of,
        settings=get_settings(),
    )
    second = ensure_transactions_loaded(
        db_session,
        client,
        lon=lon,
        lat=lat,
        radius_m=radius_m,
        window_start=window_start,
        window_end=as_of,
        settings=get_settings(),
    )
    db_session.flush()
    assert first.limitation is None
    assert second.limitation is None
    assert calls["n"] == 1
    stored = get_coverage_cells(db_session, source=TRANSACTION_SOURCE, cells=cells)
    assert len(stored) == len(cells)
    assert all(row.status == "complete" for row in stored)
