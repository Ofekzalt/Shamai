from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.infrastructure.gis.arcgis import HttpGetClient, arcgis_query, envelope_wgs84
from app.modules.planning.constants import XPLAN_META_LAYER, XPLAN_POLYGON_LAYER


def _ring_to_wkt(rings: list[list[list[float]]]) -> str:
    parts: list[str] = []
    for ring in rings:
        coords = ", ".join(f"{x} {y}" for x, y in ring)
        parts.append(f"({coords})")
    return f"MULTIPOLYGON(({','.join(parts)}))"


def parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    text = str(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def fetch_polygons_in_bbox(
    client: HttpGetClient,
    *,
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
) -> list[dict[str, Any]]:
    payload = arcgis_query(
        client,
        XPLAN_POLYGON_LAYER,
        where="1=1",
        out_fields="pl_number,mp_id,pl_name",
        return_geometry=True,
        result_record_count=500,
        geometry=envelope_wgs84(minx, miny, maxx, maxy),
        geometry_type="esriGeometryEnvelope",
        in_sr=4326,
        spatial_rel="esriSpatialRelIntersects",
    )
    return payload.get("features", [])


def fetch_plan_metadata(
    client: HttpGetClient,
    *,
    pl_number: str,
) -> dict[str, Any] | None:
    where = f"pl_number = '{pl_number.replace(chr(39), chr(39) * 2)}'"
    payload = arcgis_query(
        client,
        XPLAN_META_LAYER,
        where=where,
        out_fields="pl_number,depositing_date,pl_date_advertise,last_update_date",
        return_geometry=False,
        result_record_count=1,
    )
    features = payload.get("features", [])
    if not features:
        return None
    return features[0].get("attributes", {})


def feature_to_wkt(feature: dict[str, Any]) -> str | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None
    rings = geometry.get("rings")
    if not rings:
        return None
    return _ring_to_wkt(rings)
