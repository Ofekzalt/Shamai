from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

from app.core.logging import host_from_url, log_extra

logger = logging.getLogger(__name__)


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
    host = host_from_url(url)
    started = time.perf_counter()
    try:
        response = client.get(url, params=params)
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "external request failed",
            extra=log_extra(
                event="external.request_failed",
                host=host,
                duration_ms=duration_ms,
            ),
        )
        raise
    duration_ms = int((time.perf_counter() - started) * 1000)
    status_code = getattr(response, "status_code", None)
    if status_code is not None and status_code >= 400:
        logger.warning(
            "external request failed",
            extra=log_extra(
                event="external.request_failed",
                host=host,
                status_code=status_code,
                duration_ms=duration_ms,
            ),
        )
    if hasattr(response, "json"):
        payload = response.json()
    else:
        payload = json.loads(response)
    if payload.get("error"):
        message = payload["error"].get("message", "ArcGIS error")
        logger.warning(
            "external request failed",
            extra=log_extra(
                event="external.request_failed",
                host=host,
                duration_ms=duration_ms,
            ),
        )
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
