from __future__ import annotations

from app.infrastructure.gis.arcgis import arcgis_query
from app.modules.property_data.constants import TLV_ADDRESS_LAYER
from app.modules.property_data.providers.geocode_tlv import _escape


def fetch_street_centroid(
    client,
    *,
    street: str,
) -> tuple[float, float] | None:
    where = f"t_rechov = '{_escape(street)}'"
    payload = arcgis_query(
        client,
        TLV_ADDRESS_LAYER,
        where=where,
        out_fields="lon,lat",
        return_geometry=False,
        result_record_count=1,
    )
    features = payload.get("features", [])
    if not features:
        return None
    attrs = features[0].get("attributes", {})
    lon = attrs.get("lon")
    lat = attrs.get("lat")
    if lon is None or lat is None:
        return None
    return float(lon), float(lat)
