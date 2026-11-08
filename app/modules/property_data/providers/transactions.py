from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlencode

from app.core.logging import host_from_url, log_extra
from app.modules.property_data.constants import (
    ODATA_DATASTORE_RESOURCE,
    ODATA_SEARCH_URL,
    SOURCE_ROW_FIELD,
    TLV_CITY,
)
from app.modules.property_data.dto import TransactionRecord

logger = logging.getLogger(__name__)


class HttpGetClient(Protocol):
    def get(self, url: str) -> Any: ...


def _parse_deal_datetime(value: str) -> datetime:
    cleaned = value.replace("T", " ").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized dealdatetime: {value!r}")


def _parse_price_agorot(raw: object) -> int | None:
    if raw is None:
        return None
    text = str(raw).replace(",", "").replace(" ", "").strip()
    if not text:
        return None
    return int(round(float(text) * 100))


def record_in_window(raw: dict[str, Any], *, window_start: datetime, window_end: datetime) -> bool:
    deal = raw.get("dealdatetime")
    if deal is None:
        return False
    effective = _parse_deal_datetime(str(deal))
    return window_start <= effective <= window_end


def normalize_record(raw: dict[str, Any]) -> TransactionRecord | None:
    row_id = raw.get(SOURCE_ROW_FIELD) or raw.get("row_num") or raw.get("id")
    deal = raw.get("dealdatetime")
    price_agorot = _parse_price_agorot(raw.get("dealamount") or raw.get("price"))
    lon = raw.get("lon") or raw.get("longitude")
    lat = raw.get("lat") or raw.get("latitude")
    if row_id is None or deal is None or price_agorot is None:
        return None
    if lon is None or lat is None:
        return None
    size = raw.get("area") or raw.get("size_sqm") or raw.get("assetroomno")
    if size is None and raw.get("dealnature") is not None:
        nature = str(raw.get("dealnature")).replace(",", "").strip()
        if nature.replace(".", "", 1).isdigit():
            size = nature
    rooms = raw.get("rooms")
    floor = raw.get("floor") or raw.get("floorno")
    neighborhood = raw.get("neighborhood") or raw.get("shchuna")
    return TransactionRecord(
        source_row_id=str(row_id),
        price_agorot=price_agorot,
        size_sqm=float(size) if size is not None else None,
        rooms=float(rooms) if rooms is not None else None,
        floor=int(floor) if floor is not None and str(floor).isdigit() else None,
        neighborhood=str(neighborhood) if neighborhood is not None else None,
        lon=float(lon),
        lat=float(lat),
        effective_at=_parse_deal_datetime(str(deal)),
        published_at=None,
    )


def fetch_tlv_window(
    client: HttpGetClient,
    *,
    window_start: datetime,
    window_end: datetime,
    limit: int = 1000,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int, bool]:
    del window_start, window_end
    filters = json.dumps({"city_name": TLV_CITY}, ensure_ascii=False)
    query = urlencode(
        {
            "resource_id": ODATA_DATASTORE_RESOURCE,
            "limit": str(limit),
            "offset": str(offset),
            "filters": filters,
        }
    )
    url = f"{ODATA_SEARCH_URL}?{query}"
    response = client.get(url)
    status = getattr(response, "status_code", 200)
    if status >= 400:
        logger.warning(
            "external request failed",
            extra=log_extra(
                event="external.request_failed",
                host=host_from_url(ODATA_SEARCH_URL),
                status_code=status,
            ),
        )
        raise RuntimeError(f"odata datastore_search HTTP {status}")
    payload = response.json() if hasattr(response, "json") else json.loads(response)
    result = payload.get("result", {})
    records = result.get("records", [])
    total = int(result.get("total", len(records)))
    last_page = offset + len(records) >= total or len(records) < limit
    return records, total, last_page
