from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.infrastructure.gis.arcgis import HttpGetClient, arcgis_query
from app.modules.property_data.constants import GEOCODE_SOURCE, TLV_ADDRESS_LAYER
from app.modules.property_data.dto import GeocodeRecord


def _escape(value: str) -> str:
    return value.replace("'", "''")


def fetch_geocode(
    client: HttpGetClient,
    *,
    street: str,
    house_number: str,
) -> GeocodeRecord | None:
    where = f"t_rechov = '{_escape(street)}' AND ms_bayit = '{_escape(house_number)}'"
    payload = arcgis_query(
        client,
        TLV_ADDRESS_LAYER,
        where=where,
        out_fields="t_rechov,ms_bayit,lon,lat,t_shchuna",
        return_geometry=False,
        result_record_count=1,
    )
    features = payload.get("features", [])
    if not features:
        return None
    attrs: dict[str, Any] = features[0].get("attributes", {})
    lon = attrs.get("lon")
    lat = attrs.get("lat")
    if lon is None or lat is None:
        return None
    neighborhood = attrs.get("t_shchuna")
    return GeocodeRecord(
        street=street,
        house_number=house_number,
        lon=float(lon),
        lat=float(lat),
        source=GEOCODE_SOURCE,
        retrieved_at=datetime.now(tz=UTC),
        neighborhood=str(neighborhood) if neighborhood is not None else None,
    )
