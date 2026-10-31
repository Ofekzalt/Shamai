from __future__ import annotations

import json
from typing import Any, Protocol


class HttpGetClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


def arcgis_query(
    client: HttpGetClient,
    base_url: str,
    *,
    where: str,
    out_fields: str,
    return_geometry: bool,
    result_record_count: int | None = None,
    geometry: str | None = None,
    geometry_type: str | None = None,
    in_sr: int | None = None,
    spatial_rel: str | None = None,
) -> dict[str, Any]:
    params: dict[str, str] = {
        "where": where,
        "outFields": out_fields,
        "returnGeometry": "true" if return_geometry else "false",
        "f": "json",
    }
    if result_record_count is not None:
        params["resultRecordCount"] = str(result_record_count)
    if geometry is not None:
        params["geometry"] = geometry
    if geometry_type is not None:
        params["geometryType"] = geometry_type
    if in_sr is not None:
        params["inSR"] = str(in_sr)
    if spatial_rel is not None:
        params["spatialRel"] = spatial_rel
    url = base_url if "?" not in base_url else base_url.split("?", 1)[0]
    response = client.get(url, params=params)
    if hasattr(response, "json"):
        payload = response.json()
    else:
        payload = json.loads(response)
    if payload.get("error"):
        message = payload["error"].get("message", "ArcGIS error")
        raise RuntimeError(message)
    return payload


def envelope_wgs84(minx: float, miny: float, maxx: float, maxy: float) -> str:
    return json.dumps(
        {
            "xmin": minx,
            "ymin": miny,
            "xmax": maxx,
            "ymax": maxy,
            "spatialReference": {"wkid": 4326},
        }
    )
