from __future__ import annotations

from app.infrastructure.gis.coverage_grid import lon_lat_to_cell


def test_lon_lat_to_cell_is_stable() -> None:
    first = lon_lat_to_cell(34.7818, 32.0853)
    second = lon_lat_to_cell(34.7818, 32.0853)
    assert first == second
