from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.gis.arcgis import HttpGetClient
from app.modules.evidence.store import upsert_evidence
from app.modules.property_data import service as property_data_service


class GeocodeToolResult(BaseModel):
    lon: float
    lat: float
    neighborhood: str | None
    evidence_ids: list[uuid.UUID]


def geocode(
    session: Session,
    client: HttpGetClient,
    *,
    run_id: uuid.UUID,
    street: str,
    house_number: str,
) -> GeocodeToolResult:
    record = property_data_service.geocode_address(
        session,
        client,
        street=street,
        house_number=house_number,
    )
    retrieved_at = datetime.now(tz=UTC)
    params = {"street": street, "house_number": house_number}
    payload = {
        "street": record.street,
        "house_number": record.house_number,
        "lon": record.lon,
        "lat": record.lat,
        "neighborhood": record.neighborhood,
        "source": record.source,
    }
    evidence = upsert_evidence(
        session,
        run_id=run_id,
        tool_name="geocode",
        params=params,
        payload=payload,
        source=record.source,
        retrieved_at=retrieved_at,
        coverage_status=None,
    )
    return GeocodeToolResult(
        lon=record.lon,
        lat=record.lat,
        neighborhood=record.neighborhood,
        evidence_ids=[evidence.id],
    )
