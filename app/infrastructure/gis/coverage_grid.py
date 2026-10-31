from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from pyproj import Transformer

CELL_SIZE_M = 250
_WGS84_TO_ITM = Transformer.from_crs("EPSG:4326", "EPSG:2039", always_xy=True)


@dataclass(frozen=True)
class Cell:
    x: int
    y: int


def lon_lat_to_cell(lon: float, lat: float) -> Cell:
    easting, northing = _WGS84_TO_ITM.transform(lon, lat)
    return Cell(x=int(easting // CELL_SIZE_M), y=int(northing // CELL_SIZE_M))


def cells_for_bbox(minx: float, miny: float, maxx: float, maxy: float) -> set[Cell]:
    corners = [
        lon_lat_to_cell(minx, miny),
        lon_lat_to_cell(maxx, miny),
        lon_lat_to_cell(minx, maxy),
        lon_lat_to_cell(maxx, maxy),
    ]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    return {Cell(x, y) for x in range(min(xs), max(xs) + 1) for y in range(min(ys), max(ys) + 1)}


def window_covers(
    *,
    window_start: datetime,
    window_end: datetime | None,
    requested_start: datetime,
    requested_end: datetime,
) -> bool:
    if window_start > requested_start:
        return False
    if window_end is not None and window_end < requested_end:
        return False
    return True


def open_window_stale(*, window_end: datetime | None, lag_days: int, now: datetime) -> bool:
    if window_end is None:
        return False
    return window_end + timedelta(days=lag_days) < now
