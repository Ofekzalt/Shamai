from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import AddressNotGeocodedError
from app.core.logging import log_extra
from app.infrastructure.gis.arcgis import HttpGetClient
from app.modules.property_data.constants import GEOCODE_SOURCE
from app.modules.property_data.dto import (
    ComparableCandidate,
    ComparableCandidatesQuery,
    CoverageStatus,
    GeocodeRecord,
    NearbyTransactionsQuery,
    ServiceResult,
)
from app.modules.property_data.providers import geocode_tlv
from app.modules.property_data.repository import (
    get_geocode,
    list_knn_candidates,
    list_nearby_transactions_as_of,
    upsert_geocode,
)
from app.modules.property_data.window import transaction_window_start

logger = logging.getLogger(__name__)


def geocode_address(
    session: Session,
    client: HttpGetClient,
    *,
    street: str,
    house_number: str,
) -> GeocodeRecord:
    cached = get_geocode(session, street=street, house_number=house_number)
    if cached is not None:
        logger.debug(
            "geocode cache hit",
            extra=log_extra(event="geocode.cache_hit", source=cached.source),
        )
        return GeocodeRecord(
            street=cached.street,
            house_number=cached.house_number,
            lon=cached.lon,
            lat=cached.lat,
            source=cached.source,
            retrieved_at=cached.retrieved_at,
            neighborhood=cached.neighborhood,
        )
    record = geocode_tlv.fetch_geocode(client, street=street, house_number=house_number)
    if record is None:
        logger.warning(
            "geocode failed",
            extra=log_extra(event="geocode.failed", source=GEOCODE_SOURCE),
        )
        raise AddressNotGeocodedError(street, house_number)
    upsert_geocode(session, record)
    session.flush()
    return record


def nearby_transactions(
    session: Session,
    client: HttpGetClient,
    query: NearbyTransactionsQuery,
) -> ServiceResult[list]:
    from app.core.config import get_settings
    from app.modules.property_data.service_transactions import ensure_transactions_loaded

    settings = get_settings()
    load = ensure_transactions_loaded(
        session,
        client,
        lon=query.lon,
        lat=query.lat,
        window_start=transaction_window_start(query.as_of),
        window_end=query.as_of,
        settings=settings,
        radius_m=query.radius_m,
    )
    rows = list_nearby_transactions_as_of(
        session,
        lon=query.lon,
        lat=query.lat,
        radius_m=query.radius_m,
        as_of=query.as_of,
    )
    if load.limitation is not None:
        logger.warning(
            "coverage incomplete",
            extra=log_extra(event="coverage.incomplete", source="odata_nadlan"),
        )
        return ServiceResult(
            data=rows,
            coverage_status=CoverageStatus.INCOMPLETE,
            limitation=load.limitation,
        )
    return ServiceResult(data=rows, coverage_status=CoverageStatus.COMPLETE)


def comparable_candidates(
    session: Session,
    client: HttpGetClient,
    query: ComparableCandidatesQuery,
) -> ServiceResult[list[ComparableCandidate]]:
    from app.core.config import get_settings
    from app.modules.property_data.service_transactions import ensure_transactions_loaded

    settings = get_settings()
    load = ensure_transactions_loaded(
        session,
        client,
        lon=query.lon,
        lat=query.lat,
        window_start=transaction_window_start(query.as_of),
        window_end=query.as_of,
        settings=settings,
        radius_m=query.radius_m,
    )
    rows = list_knn_candidates(
        session,
        lon=query.lon,
        lat=query.lat,
        radius_m=query.radius_m,
        as_of=query.as_of,
        limit=query.limit,
    )
    logger.debug(
        "knn candidates",
        extra=log_extra(event="knn.candidates", record_count=len(rows)),
    )
    if load.limitation is not None:
        logger.warning(
            "coverage incomplete",
            extra=log_extra(event="coverage.incomplete", source="odata_nadlan"),
        )
        return ServiceResult(
            data=rows,
            coverage_status=CoverageStatus.INCOMPLETE,
            limitation=load.limitation,
        )
    return ServiceResult(data=rows, coverage_status=CoverageStatus.COMPLETE)
