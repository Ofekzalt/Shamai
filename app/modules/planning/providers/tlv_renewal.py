from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.infrastructure.gis.arcgis import HttpGetClient, arcgis_query, envelope_wgs84
from app.modules.planning.constants import TLV_RENEWAL_LAYER


def _ring_to_wkt(rings: list[list[list[float]]]) -> str:
    parts: list[str] = []
    for ring in rings:
        coords = ", ".join(f"{x} {y}" for x, y in ring)
        parts.append(f"({coords})")
    return f"MULTIPOLYGON(({','.join(parts)}))"


def fetch_renewal_in_bbox(
    client: HttpGetClient,
    *,
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
) -> list[dict[str, Any]]:
    payload = arcgis_query(
        client,
        TLV_RENEWAL_LAYER,
        where="sw_hitchadshut_ironit=1",
        out_fields="taba,t_status,tr_shinuy_status,OBJECTID",
        return_geometry=True,
        result_record_count=500,
        geometry=envelope_wgs84(minx, miny, maxx, maxy),
        geometry_type="esriGeometryEnvelope",
        in_sr=4326,
        spatial_rel="esriSpatialRelIntersects",
    )
    return payload.get("features", [])


def feature_to_wkt(feature: dict[str, Any]) -> str | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None
    rings = geometry.get("rings")
    if not rings:
        return None
    return _ring_to_wkt(rings)


def snapshot_effective_at(attrs: dict[str, Any], *, retrieved_at: datetime) -> datetime:
    status_date = attrs.get("tr_shinuy_status") or attrs.get("t_status")
    parsed = _parse_date(status_date)
    return parsed or retrieved_at


def _parse_date(value: Any) -> datetime | None:
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
